from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ServiceError:
    message: str
    status: int = 400
    payload: dict[str, Any] | None = None

    def as_payload(self) -> dict[str, Any]:
        if self.payload is not None:
            return self.payload

        return {"error": self.message}


@dataclass(slots=True)
class AuthIntent:
    otp: str
    temp_token: str
    redirect_url: str


@dataclass(slots=True)
class CallbackVerification:
    action: str
    expires_at: int
    is_logged_in: bool = False


@dataclass(slots=True)
class PasswordVerification:
    account: str
    password: str
    state_key: str
