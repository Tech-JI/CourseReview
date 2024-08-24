# Generated by Django 5.0.8 on 2024-08-22 14:17

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CrawledData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "resource",
                    models.CharField(db_index=True, max_length=128, unique=True),
                ),
                (
                    "data_type",
                    models.CharField(
                        choices=[
                            ("medians", "Medians"),
                            ("orc_department_courses", "ORC Department Courses"),
                            ("course_timetable", "Course Timetable"),
                        ],
                        max_length=32,
                    ),
                ),
                ("current_data", models.JSONField()),
                ("pending_data", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]