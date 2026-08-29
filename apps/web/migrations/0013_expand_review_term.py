from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("web", "0012_vote_web_vote_course__b117a9_idx")]

    operations = [
        migrations.AlterField(
            model_name="review",
            name="term",
            field=models.CharField(db_index=True, max_length=4),
        ),
    ]
