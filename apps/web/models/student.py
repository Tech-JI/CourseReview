from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models


class StudentManager(models.Manager):
    pass


class Student(models.Model):
    objects = StudentManager()

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return str(self.user)
