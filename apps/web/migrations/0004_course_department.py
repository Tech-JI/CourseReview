# Generated by Django 5.0.8 on 2024-09-01 06:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0003_alter_course_unique_together_course_course_code_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='department',
            field=models.CharField(db_index=True, default='', max_length=5),
        ),
    ]