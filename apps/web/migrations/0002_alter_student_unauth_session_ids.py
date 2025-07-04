# Generated by Django 5.0.8 on 2024-08-22 13:47

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="unauth_session_ids",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=32, unique=True),
                blank=True,
                default=list,
                size=None,
            ),
        ),
    ]
