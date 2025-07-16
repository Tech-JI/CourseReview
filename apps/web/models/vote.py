from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models, transaction

from .course import Course


class VoteManager(models.Manager):
    @transaction.atomic
    def vote(self, value, course_id, category, user):
        is_unvote = False

        # Allow values from 1 to 5, or 0 for unvote
        if value != 0 and (value < 1 or value > 5):
            return None, is_unvote

        course = Course.objects.get(id=course_id)
        vote, created = self.get_or_create(course=course, category=category, user=user)

        # Handle unvote (when same value is clicked again)
        if not created and vote.value == value:
            vote.value = 0
            is_unvote = True
        else:
            vote.value = value
            is_unvote = value == 0

        # Recalculate average score
        new_score = None
        if category == Vote.CATEGORIES.QUALITY:
            new_score = self._calculate_average_score(course, category)
            course.quality_score = new_score
        elif category == Vote.CATEGORIES.DIFFICULTY:
            new_score = self._calculate_average_score(course, category)
            course.difficulty_score = new_score

        course.save()
        vote.save()
        return new_score, is_unvote

    def _calculate_average_score(self, course, category):
        """Calculate the average score for a course in a specific category"""
        votes = self.filter(course=course, category=category).exclude(value=0)
        if not votes.exists():
            return 0

        total_score = sum(vote.value for vote in votes)
        vote_count = votes.count()
        # Return average rounded to 1 decimal place
        return round(total_score / vote_count, 1)

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

    def __unicode__(self):
        return "{} {} for {} by {}".format(
            self.category.capitalize(),
            self.vote_type(),
            self.course.short_name(),
            self.user.username,
        )

    def vote_type(self):
        if self.is_upvote():
            return "upvote"
        elif self.is_downvote():
            return "downvote"
        else:
            return "neutral vote"

    def is_upvote(self):
        return self.value > 0

    def is_downvote(self):
        return self.value < 0

    def is_vote(self):
        return self.is_upvote() or self.is_downvote()
