import random
import json
import httpx
import asyncio
import time
import threading
import logging
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.contrib.auth.models import User
from django_redis import get_redis_connection
from django.conf import settings
from apps.web.models import Student

VERIFICATION_QUESTION_ID = 10424106
STUDENT_ID_QUESTION_ID = "10424105"

# 存储每个 session_id 对应的事件队列（SSE 推送用）
sse_queues = {}


def sse_status(request):
    """
    SSE endpoint for real-time status updates.
    """
    # Force Django to create a session if one doesn't exist
    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key
    if not session_id:
        return JsonResponse({"error": "No session"}, status=403)

    # Use the default cache alias for Redis connection
    r = get_redis_connection("default")

    def event_stream():
        for _ in range(300):  # 最多等待 300 秒
            try:
                data = r.get(f"session:{session_id}")
                if data:
                    payload = json.loads(data.decode("utf-8"))
                    if payload.get("status") == "fully_verified":
                        yield f"data: {json.dumps(payload)}\n\n"
                        break
            except Exception as e:
                print(f"Error in event_stream: {e}")
                # Even if there's an error, continue the loop

            time.sleep(1)
        else:
            # 超时返回
            yield f"data: {json.dumps({'status': 'timeout'})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    #    response['Connection'] = 'keep-alive'
    response["Access-Control-Allow-Origin"] = "*"

    return response


def verify_page(request):
    """用户访问验证页面：生成验证码 + 显示 Turnstile"""
    # Force session creation
    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key
    r = get_redis_connection("default")
    r.delete(f"session:{session_id}")  # ✅ 清空旧状态

    return render(
        request,
        "verify.html",
        {
            "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY,
            "SURVEY_URL": settings.SURVEY_URL,
        },
    )


@csrf_exempt
def verify_turnstile(request):
    token = request.POST.get("cf-turnstile-response")
    ip = request.META.get("REMOTE_ADDR")
    if not token:
        return JsonResponse({"success": False, "error": "Missing token"}, status=400)

    async def verify():
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": settings.TURNSTILE_SECRET_KEY,
                    "response": token,
                    "remoteip": ip,
                },
            )
            return resp.json()

    result = asyncio.run(verify())
    if not result.get("success"):
        return JsonResponse({"success": False, "error": "Turnstile failed"}, status=403)

    # Ensure session exists
    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key
    if not session_id:
        return JsonResponse({"success": False, "error": "No session"}, status=403)

    r = get_redis_connection("default")

    # ✅ 成功后生成验证码并写入 Redis
    code = "".join(random.choices("0123456789", k=8))
    payload = {"code": code, "status": "turnstile_verified"}
    r.setex(f"session:{session_id}", 300, json.dumps(payload))
    print("Payload received:", json.dumps(payload, indent=2))
    print("Matching code:", code)

    return JsonResponse({"success": True, "code": code})


@csrf_exempt
def webhook(request):
    print("✅ Webhook 被调用了，method=", request.method)

    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "detail": "Only POST allowed"}, status=405
        )

    try:
        raw_body = request.body.decode("utf-8")
        print("Webhook Raw Body:", raw_body)  # 打印收到的原始 JSON

        payload = json.loads(raw_body)
        print("✅ JSON 解析成功")

        submissions = payload.get("answer_sheet", [])
        print(f"submissions: {submissions}")

        r = get_redis_connection("default")
        matched_session_id = None

        for submission in submissions:
            # 提取验证码和姓名
            code = None
            name = None
            student_id = None

            for answer in submission.get("answers", []):
                if str(answer["question"]["id"]) == str(VERIFICATION_QUESTION_ID):
                    code = str(answer["answer"]).strip()
                elif str(answer["question"]["id"]) == str(STUDENT_ID_QUESTION_ID):
                    student_id = str(answer["answer"]).strip()

            name = submission["user"]["name"]

            if not code or not student_id:
                print(f"缺少验证码或学号: code={code}, student_id={student_id}")
                continue

            print(f"找到用户答案: code={code}, name={name}, student_id={student_id}")

            # 查找匹配的 session
            for key in r.keys("session:*"):
                value = r.get(key)
                if not value:
                    continue
                try:
                    data = json.loads(value)
                except json.JSONDecodeError:
                    print(f"JSON解析失败 for key {key}")
                    continue

                if (
                    data.get("status") == "turnstile_verified"
                    and str(data.get("code")).strip() == code.strip()
                ):
                    new_data = {
                        "code": code,
                        "status": "fully_verified",
                        "name": name,
                        "student_id": student_id,  # 存储学号
                        "verified_at": int(time.time()),
                    }
                    r.setex(key, 3600, json.dumps(new_data))
                    # 正确提取 session_id (去除 "session:" 前缀)
                    matched_session_id = key.decode().split(":", 1)[1]
                    print(f"验证成功，写入 redis：{key} => {new_data}")
                    break

        if matched_session_id:
            return JsonResponse(
                {"success": True, "code": code, "session_id": matched_session_id}
            )
        else:
            return JsonResponse(
                {"success": False, "error": "未找到匹配的会话"}, status=404
            )

    except json.JSONDecodeError as e:
        print("❌ JSON 解析失败:", e)
        return JsonResponse({"status": "error", "detail": "Invalid JSON"}, status=400)
    except Exception as e:
        print("❌ Webhook 内部错误:", str(e))
        return JsonResponse({"status": "error", "detail": str(e)}, status=500)


@csrf_exempt
def complete_login(request):
    """
    API endpoint to complete the login process after verification.
    """
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "detail": "Only POST allowed"}, status=405
        )

    try:
        # 从请求体中获取 session_id
        # 如果前端通过 POST 发送 JSON，需要这样解析
        # 如果是通过表单或者查询参数传递，需要相应调整
        data = json.loads(request.body.decode("utf-8"))
        session_id = data.get("session_id")
    except (json.JSONDecodeError, KeyError):
        # Fallback to query parameter if JSON parsing fails or key is missing
        session_id = request.GET.get("session_id") or request.POST.get("session_id")

    if not session_id:
        return JsonResponse(
            {"status": "error", "detail": "Missing session_id"}, status=400
        )

    r = get_redis_connection("default")
    key = f"session:{session_id}"
    value = r.get(key)

    if not value:
        return JsonResponse(
            {"status": "error", "detail": "Session not found or expired"}, status=404
        )

    try:
        session_data = json.loads(value)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "detail": "Invalid session data"}, status=500
        )

    if session_data.get("status") != "fully_verified":
        return JsonResponse(
            {"status": "error", "detail": "Session not fully verified"}, status=400
        )

    student_id = session_data.get("student_id")
    name = session_data.get("name")

    if not student_id or not name:
        return JsonResponse(
            {"status": "error", "detail": "Missing student_id or name in session"},
            status=500,
        )

    # 创建或获取 User 和 Student 对象
    # 使用学号作为用户名
    username = student_id
    try:
        user = User.objects.get(username=username)
        print(f"用户 {username} 已存在")
    except User.DoesNotExist:
        # 创建新用户，不设置可用密码
        user = User(
            username=username,
            first_name=name,  # 可以根据需要调整
            is_active=True,  # 直接激活
        )
        user.set_unusable_password()  # 设置为不可用密码
        user.save()
        print(f"创建新用户 {username}")

    # 创建或获取 Student 对象 - 使用 get_or_create
    # 此登录系统不使用密码，也不需要 confirmation_link
    student, created = Student.objects.get_or_create(
        user=user, defaults={"unauth_session_ids": []}
    )

    if created:
        print(f"创建新的 Student 对象 for user {username}")
    else:
        print(f"Student 对象已存在 for user {username}")

    # 登录用户
    login(request, user)
    print(f"用户 {username} 登录成功")

    # 可以选择性地从 Redis 中删除 session 数据，或者保留一段时间
    # r.delete(key)

    return JsonResponse(
        {
            "status": "success",
            "detail": "Login completed",
            "username": user.username,
            "name": name,
        }
    )


# 新增的 API 端点：为前端 Vue 组件提供配置和 session 信息
def verify_config(request):
    """
    API endpoint to provide configuration and session info for the Vue login component.
    """
    # Force session creation
    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key

    if not session_id:
        return JsonResponse({"error": "无法创建 session"}, status=500)

    # 清空旧状态
    r = get_redis_connection("default")
    r.delete(f"session:{session_id}")

    return JsonResponse(
        {
            "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY,
            "SURVEY_URL": settings.SURVEY_URL,
            "session_id": session_id,
        }
    )
