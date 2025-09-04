from django.urls import path
from apps.verifier import views

urlpatterns = [
    path('', views.verify_page, name="verify_page"),
    path("turnstile/", views.verify_turnstile, name="verify_turnstile"),
    path("webhook/", views.webhook, name="webhook"),
    path("sse/", views.sse_status, name="sse_status"),
    path("complete_login/", views.complete_login, name="complete_login"),
    path("api/config/", views.verify_config, name="verify_config"),  # 为Vue组件提供配置和session信息
]

