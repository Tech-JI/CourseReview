from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models


class ReviewManager(models.Manager):
    def user_can_write_review(self, user, course):
        return not self.filter(user=user, course=course).exists()

    def num_reviews_for_user(self, user):
        return self.filter(user=user).count()

    def get_user_review_for_course(self, user, course):
        """
        Get the review written by a user for a specific course.
        Returns the Review object if found, None otherwise.
        If multiple reviews exist, returns the most recent one.
        """
        try:
            return self.get(user=user, course=course)
        except self.model.DoesNotExist:
            return None
        except self.model.MultipleObjectsReturned:
            # If somehow there are multiple reviews, return the most recent one
            return self.filter(user=user, course=course).order_by("-created_at").first()

    def get_kudos_count(self, review_id):
        """Get the number of kudos for a specific review"""
        return self.get(id=review_id).votes.filter(is_kudos=True).count()

    def get_dislike_count(self, review_id):
        """Get the number of dislikes for a specific review"""
        return self.get(id=review_id).votes.filter(is_kudos=False).count()

    def get_vote_counts(self, review_id):
        """Get both kudos and dislike counts for a specific review"""
        kudos_count = self.get_kudos_count(review_id)
        dislike_count = self.get_dislike_count(review_id)
        return kudos_count, dislike_count


class Review(models.Model):
    objects = ReviewManager()

    MANUAL_SENTIMENT_LABELER = "Manual"
    AUTOMATED_SENTIMENT_LABELER = "Classifier"
    SENTIMENT_LABELERS = (
        (MANUAL_SENTIMENT_LABELER, "Sentiment manually recorded"),
        (AUTOMATED_SENTIMENT_LABELER, "Sentiment based on classifier"),
    )

    course = models.ForeignKey("Course", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    professor = models.CharField(max_length=255, db_index=True, blank=False)
    term = models.CharField(max_length=3, db_index=True, blank=False)
    comments = models.TextField(blank=False)

    sentiment_labeler = models.CharField(
        max_length=64,
        choices=SENTIMENT_LABELERS,
        default=None,
        db_index=True,
        null=True,
        blank=True,
    )
    difficulty_sentiment = models.FloatField(default=None, null=True, blank=True)
    quality_sentiment = models.FloatField(default=None, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "{} {} {}: {}".format(
            self.course.short_name(), self.professor, self.term, self.comments
        )
