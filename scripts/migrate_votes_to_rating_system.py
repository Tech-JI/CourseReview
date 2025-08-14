#!/usr/bin/env python
"""
Script to migrate existing votes to new rating system.
This script converts old +1/-1 votes to the new 1-5 rating system.
"""

import os
import sys

import django

# Add the project directory to the path
sys.path.insert(0, "/home/nuoxi/CourseReview")

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
django.setup()

from django.db import transaction

from apps.web.models import Course, Vote


def migrate_votes():
    """
    Migrate existing votes to new rating system:
    - Old +1 votes become 4 (good rating)
    - Old -1 votes become 2 (poor rating)
    - Old 0 votes remain 0 (unvoted)
    """
    print("Starting vote migration...")

    with transaction.atomic():
        # Convert +1 votes to 4 (good rating)
        positive_votes = Vote.objects.filter(value=1)
        positive_count = positive_votes.count()
        positive_votes.update(value=4)
        print(f"Converted {positive_count} positive votes to rating 4")

        # Convert -1 votes to 2 (poor rating)
        negative_votes = Vote.objects.filter(value=-1)
        negative_count = negative_votes.count()
        negative_votes.update(value=2)
        print(f"Converted {negative_count} negative votes to rating 2")

        # Recalculate all course scores
        print("Recalculating course scores...")
        courses = Course.objects.all()
        for course in courses:
            # Recalculate quality score
            quality_votes = Vote.objects.filter(
                course=course, category=Vote.CATEGORIES.QUALITY
            ).exclude(value=0)

            if quality_votes.exists():
                avg_quality = (
                    sum(vote.value for vote in quality_votes) / quality_votes.count()
                )
                course.quality_score = round(avg_quality, 1)
            else:
                course.quality_score = 0.0

            # Recalculate difficulty score
            difficulty_votes = Vote.objects.filter(
                course=course, category=Vote.CATEGORIES.DIFFICULTY
            ).exclude(value=0)

            if difficulty_votes.exists():
                avg_difficulty = (
                    sum(vote.value for vote in difficulty_votes)
                    / difficulty_votes.count()
                )
                course.difficulty_score = round(avg_difficulty, 1)
            else:
                course.difficulty_score = 0.0

            course.save()

        print(f"Updated scores for {courses.count()} courses")
        print("Vote migration completed successfully!")


if __name__ == "__main__":
    migrate_votes()
