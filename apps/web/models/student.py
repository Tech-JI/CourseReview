from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.mail import send_mail
from django.db import models
from django.urls import reverse

from lib import constants

from .vote import Vote


class StudentManager(models.Manager):
    def is_valid_sjtu_student_email(self, email):
        email_components = email.split("@")
        if len(email_components) != 2:
            return False
        domain = email_components[1]
        return domain == "sjtu.edu.cn"


class Student(models.Model):
    objects = StudentManager()

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    confirmation_link = models.CharField(max_length=16, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    unauth_session_ids = ArrayField(
        base_field=models.CharField(max_length=32, unique=True),
        default=list,
        blank=True,
    )

    def send_confirmation_link(self, request):
        full_link = (
            request.build_absolute_uri(reverse("confirmation"))
            + "?link="
            + self.confirmation_link
        )
        if not settings.DEBUG:
            send_mail(
                "Your confirmation link",
                "Please navigate to the following confirmation link: " + full_link,
                constants.SUPPORT_EMAIL,
                [self.user.email],
                fail_silently=False,
            )

    def can_see_recommendations(self):
        return (
            Vote.objects.num_quality_upvotes_for_user(self.user)
            >= constants.REC_UPVOTE_REQ
        )

    def __unicode__(self):
        return str(self.user)
