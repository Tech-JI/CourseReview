from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Avg

from .course import Course


class VoteManager(models.Manager):
    @transaction.atomic
    def vote(self, value, course_id, category, user):
        if value > 5 or value < 1:
            return None, False, None

        course = Course.objects.select_for_update().get(id=course_id)
        vote, created = self.get_or_create(course=course, category=category, user=user)

        is_unvote = not created and vote.value == value

        if is_unvote:
            vote.delete()
        else:
            vote.value = value
            vote.save()

        new_score = self._calculate_average_score(course, category)
        vote_count = self.get_vote_count(course, category)

        return new_score, is_unvote, vote_count

    def _calculate_average_score(self, course, category):
        result = self.filter(course=course, category=category).aggregate(
            avg_score=Avg("value")
        )
        avg = result["avg_score"]
        return round(avg, 1) if avg is not None else 0

    def get_vote_count(self, course, category):
        """Get the vote count for a course in a specific category"""
        return self.filter(course=course, category=category).count()

    def authenticated_group_courses_with_votes(self, courses, category, user):
        # returns a list of tuples: (course, user's corresponding vote or None)
        # if not authenticated, all votes are None
        if user.is_authenticated:
            return self.group_courses_with_votes(courses, category, user)
        else:
            return [(c, None) for c in courses]

    def group_courses_with_votes(self, courses, category, user):
        votes = self.filter(
            course_id__in=courses.values_list("id", flat=True),
            category=category,
            user=user,
        )

        votes_dict = {vote.course_id: vote for vote in votes}

        return [(c, votes_dict.get(c.id, None)) for c in courses]

    def for_course_and_user(self, course, user):
        votes = self.filter(course=course, user=user)

        difficulty_vote, quality_vote = None, None

        for vote in votes:
            if vote.category == Vote.CATEGORIES.DIFFICULTY:
                difficulty_vote = vote
            if vote.category == Vote.CATEGORIES.QUALITY:
                quality_vote = vote

        return difficulty_vote, quality_vote

    def num_quality_upvotes_for_user(self, user):
        return self.filter(
            user=user, category=Vote.CATEGORIES.QUALITY, value__gte=4
        ).count()


class Vote(models.Model):
    objects = VoteManager()

    class CATEGORIES:
        QUALITY = "quality"
        DIFFICULTY = "difficulty"
        CHOICES = (
            (QUALITY, "Quality"),
            (DIFFICULTY, "Difficulty"),
        )

    value = models.IntegerField(default=0)
    course = models.ForeignKey("Course", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(
        max_length=16, choices=CATEGORIES.CHOICES, db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("course", "user", "category")
        indexes = [
            models.Index(fields=["course", "category", "value"]),
        ]

    def __unicode__(self):
        return "{} for {} by {}".format(
            self.category.capitalize(),
            self.course.short_name(),
            self.user.username,
        )
