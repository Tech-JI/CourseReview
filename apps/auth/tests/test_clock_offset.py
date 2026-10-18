"""Tests for the dynamic WJ clock-offset sync mechanism in apps.auth.

Background: the WJ questionnaire platform's server clock runs slow and
drifts (~7s/day), which broke the fixed 220s submission-timestamp window.
These tests cover offset estimation from the HTTP Date header, the Redis
EWMA rolling estimate, and the offset-corrected validity check in
verify_callback_api.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from email.utils import formatdate
from http.cookies import SimpleCookie

import httpx
import pytest
from rest_framework.test import APIClient

from apps.auth import utils, views

# ---------------------------------------------------------------------------
# In-memory fake Redis (test env has no guaranteed cache container)
# ---------------------------------------------------------------------------


class FakeRedis:
    def __init__(self):
        self.store = {}

    def _bytes(self, value):
        if isinstance(value, str):
            return value.encode("utf-8")
        return value

    def get(self, key):
        v = self.store.get(key)
        return self._bytes(v) if not isinstance(v, dict) else v

    def setex(self, key, ttl, value):
        self.store[key] = value

    def getdel(self, key):
        v = self.store.pop(key, None)
        return self._bytes(v) if not isinstance(v, dict) else v

    def incr(self, key):
        n = int(self.store.get(key, 0)) + 1
        self.store[key] = str(n)
        return n

    def expire(self, key, ttl):
        return 1 if key in self.store else 0

    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)

    def hset(self, key, mapping=None):
        h = self.store.setdefault(key, {})
        h.update({mk: str(mv) for mk, mv in (mapping or {}).items()})

    def hget(self, key, field):
        h = self.store.get(key)
        if isinstance(h, dict) and field in h:
            return h[field].encode("utf-8")
        return None


@pytest.fixture
def fake_redis(monkeypatch):
    r = FakeRedis()
    monkeypatch.setattr(views, "get_redis_connection", lambda conn: r)
    monkeypatch.setattr(utils, "get_redis_connection", lambda conn: r)
    return r


# ---------------------------------------------------------------------------
# estimate_wj_clock_offset
# ---------------------------------------------------------------------------


def _response_with_date(server_offset_s, elapsed_s=0.2):
    """Fake httpx response whose Date header is server_offset_s off true time."""
    date_str = formatdate(time.time() + server_offset_s, usegmt=True)
    resp = httpx.Response(200, headers={"date": date_str})
    resp._elapsed = timedelta(seconds=elapsed_s)
    return resp


class TestEstimateWjClockOffset:
    def test_detects_slow_server(self):
        offset = utils.estimate_wj_clock_offset(_response_with_date(-230))
        assert offset is not None
        assert -232.5 < offset < -227.5

    def test_zero_offset(self):
        offset = utils.estimate_wj_clock_offset(_response_with_date(0))
        assert offset is not None
        assert abs(offset) < 2.5

    def test_missing_date_header_returns_none(self):
        resp = httpx.Response(200)
        assert utils.estimate_wj_clock_offset(resp) is None

    def test_invalid_date_header_returns_none(self):
        resp = httpx.Response(200, headers={"date": "garbage-not-a-date"})
        assert utils.estimate_wj_clock_offset(resp) is None


# ---------------------------------------------------------------------------
# record / get cached EWMA
# ---------------------------------------------------------------------------


class TestRollingEstimate:
    def test_first_sample_stored_verbatim(self, fake_redis):
        utils.record_wj_clock_offset(-230.0)
        assert utils.get_cached_wj_clock_offset() == pytest.approx(-230.0)

    def test_ewma_blend_of_two_samples(self, fake_redis):
        utils.record_wj_clock_offset(-230.0)
        utils.record_wj_clock_offset(-240.0)
        # alpha=0.3: 0.3*-240 + 0.7*-230 = -233
        assert utils.get_cached_wj_clock_offset() == pytest.approx(-233.0)

    def test_no_estimate_returns_none(self, fake_redis):
        assert utils.get_cached_wj_clock_offset() is None


# ---------------------------------------------------------------------------
# verify_callback_api validity-window integration
# ---------------------------------------------------------------------------

ACCOUNT = "testaccount"
OTP = "12345678"
ANSWER_ID = 999
VERIFY_URL = "/api/auth/verify/"


def _seed_flow(fake_redis, temp_token, initiated_at, action="signup"):
    token_hash = hashlib.sha256(temp_token.encode()).hexdigest()
    fake_redis.store[f"temp_token_state:{token_hash}"] = json.dumps(
        {"status": "pending", "action": action}
    )
    fake_redis.store[f"otp:{OTP}"] = json.dumps(
        {"temp_token": temp_token, "initiated_at": initiated_at}
    )


def _answer(offset, submitted_local, server_clock_offset="same"):
    """Build get_latest_answer payload: submission at submitted_local (our frame)
    reported in the WJ frame (= local + offset). server_clock_offset="same"
    means the fresh Date-header sample equals the true drift; pass None to
    simulate a missing sample."""
    submitted_wj = datetime.fromtimestamp(submitted_local + offset, tz=timezone.utc)
    value = offset if server_clock_offset == "same" else server_clock_offset
    data = {
        "id": ANSWER_ID,
        "submitted_at": submitted_wj.isoformat(),
        "account": ACCOUNT,
        "otp": OTP,
        "server_clock_offset": value,
    }
    return data


@pytest.fixture
def verify_client(monkeypatch, fake_redis):
    """Client + a knob to inject the mocked get_latest_answer payload."""

    state = {"answer": None}

    async def fake_get_latest_answer(action, account):
        return state["answer"], None

    monkeypatch.setattr(utils, "get_latest_answer", fake_get_latest_answer)

    def make_client(temp_token):
        client = APIClient()
        client.cookies = SimpleCookie()
        client.cookies["temp_token"] = temp_token
        return client

    def call(answer, temp_token="tok-" + "x" * 20):
        state["answer"] = answer
        return make_client(temp_token).post(
            VERIFY_URL,
            {"account": ACCOUNT, "answer_id": ANSWER_ID, "action": "signup"},
            format="json",
        )

    call.redis = fake_redis
    return call


class TestVerifyWindowWithOffset:
    def test_large_drift_accepted_after_correction(self, verify_client):
        # WJ 300s slow, user filled survey 60s after initiate.
        # Raw diff = -240s would fail the legacy 220s window; corrected
        # diff = +60s must pass.
        now = time.time()
        _seed_flow(verify_client.redis, "tok-" + "x" * 20, initiated_at=now)
        resp = verify_client(_answer(offset=-300, submitted_local=now + 60))
        assert resp.status_code == 200, resp.data

    def test_stale_replay_still_rejected(self, verify_client):
        # Genuine-looking offset, but submission an hour BEFORE initiation.
        now = time.time()
        _seed_flow(verify_client.redis, "tok-" + "x" * 20, initiated_at=now)
        resp = verify_client(_answer(offset=-300, submitted_local=now - 3600))
        assert resp.status_code == 401
        assert "validity window" in str(resp.data.get("error", ""))

    def test_no_offset_available_uses_legacy_tolerance(self, verify_client):
        # No fresh sample, no cache -> legacy 220s window on raw diff -180s.
        now = time.time()
        _seed_flow(verify_client.redis, "tok-" + "x" * 20, initiated_at=now)
        resp = verify_client(
            _answer(offset=-180, submitted_local=now + 40, server_clock_offset=None)
        )
        assert resp.status_code == 200, resp.data

    def test_legacy_tolerance_still_rejects_beyond_220(self, verify_client):
        # No offset data at all, raw diff -240s -> legacy rejects (old behavior).
        now = time.time()
        _seed_flow(verify_client.redis, "tok-" + "x" * 20, initiated_at=now)
        resp = verify_client(
            _answer(offset=-300, submitted_local=now + 60, server_clock_offset=None)
        )
        assert resp.status_code == 401

    def test_cached_offset_corrects_when_fresh_sample_missing(self, verify_client):
        # server_clock_offset missing from payload; EWMA cache says -300.
        # Raw diff -240 fails legacy 220, but cached correction accepts.
        utils.record_wj_clock_offset(-300.0)
        now = time.time()
        _seed_flow(verify_client.redis, "tok-" + "x" * 20, initiated_at=now)
        answer = _answer(offset=-300, submitted_local=now + 60)
        answer["server_clock_offset"] = None
        resp = verify_client(answer)
        assert resp.status_code == 200, resp.data

    def test_future_submission_beyond_window_rejected(self, verify_client):
        # WJ 250s fast: corrected submission sits far past OTP window upper
        # bound -> reject (also sanity-checks the +tolerance upper-bound math).
        utils.record_wj_clock_offset(250.0)
        now = time.time()
        _seed_flow(verify_client.redis, "tok-" + "x" * 20, initiated_at=now)
        resp = verify_client(
            _answer(offset=250, submitted_local=now + 750),
        )
        assert resp.status_code == 401
