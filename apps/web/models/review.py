from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Count, OuterRef, Q, Subquery


class ReviewManager(models.Manager):
    def user_can_write_review(self, user, course):
        return not self.filter(user=user, course=course).exists()

    def num_reviews_for_user(self, user):
        return self.filter(user=user).count()

    def with_votes(self, request_user=None, **kwargs):
        """
        Return queryset with annotated vote counts (kudos, dislike) and user's vote.

        Args:
            request_user: User object for user vote annotations
            **kwargs: Additional filter parameters for queryset
        """
        queryset = self.filter(**kwargs).annotate(
            kudos_count=Count("votes", filter=Q(votes__is_kudos=True), distinct=True),
            dislike_count=Count(
                "votes", filter=Q(votes__is_kudos=False), distinct=True
            ),
        )

        if request_user and request_user.is_authenticated:
            from .vote_for_review import ReviewVote

            # Define subquery: get the is_kudos value for current user's vote on this review
            vote_subquery = ReviewVote.objects.filter(
                review=OuterRef("pk"), user=request_user
            ).values("is_kudos")[:1]

            queryset = queryset.annotate(
                user_vote=Subquery(
                    vote_subquery, output_field=models.BooleanField(null=True)
                )
            )

        return queryset

    def queryset_raw(self, **kwargs):
        """
        Return base queryset without vote annotations for better performance when votes aren't needed.

        Args:
            **kwargs: Additional filter parameters
        """
        return self.filter(**kwargs)


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
