from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models, transaction

from .review import Review


class ReviewVoteManager(models.Manager):
    @transaction.atomic
    def vote(self, review_id, user, is_kudos=True):
        """
        Add a vote (kudos or dislike) to a review by a user.
        If the user has already given the same vote, remove it (cancel).
        If the user has given the opposite vote, change it.

        Args:
            review_id: ID of the review
            user: User giving the vote
            is_kudos: True for kudos, False for dislike

        Returns:
            tuple: (kudos_count, dislike_count, user_vote)
            user_vote will be True (kudos), False (dislike), or None (no vote)
        """
        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return None, None, None

        # Get or create the vote
        review_vote, created = self.get_or_create(
            review=review, user=user, defaults={"is_kudos": is_kudos}
        )

        if created:
            # New vote
            vote_value = is_kudos
        else:
            # Existing vote
            if review_vote.is_kudos == is_kudos:
                # Same vote type, remove it (cancel)
                review_vote.delete()
                vote_value = None  # User cancelled their vote
            else:
                # Change vote from kudos to dislike or vice versa
                review_vote.is_kudos = is_kudos
                review_vote.save()
                vote_value = is_kudos

        # Calculate and return updated counts and user's current vote
        review_with_votes = Review.objects.with_votes(id=review_id).first()
        if review_with_votes:
            kudos_count = review_with_votes.kudos_count
            dislike_count = review_with_votes.dislike_count
        else:
            kudos_count, dislike_count = 0, 0
        return kudos_count, dislike_count, vote_value

    def get_user_vote(self, review, user):
        """Get the user's vote for a review"""
        if not user.is_authenticated:
            return None
        try:
            return self.get(review=review, user=user).is_kudos
        except self.model.DoesNotExist:
            return None


class ReviewVote(models.Model):
    """
    Model to track kudos and dislikes given to reviews.
    Users can give either kudos (is_kudos=True) or dislike (is_kudos=False) to a review.
    Giving the same vote again will cancel it.
    """

    objects = ReviewVoteManager()

    review = models.ForeignKey("Review", on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_kudos = models.BooleanField(default=True)  # True for kudos, False for dislike

    class Meta:
        unique_together = ("review", "user")
        verbose_name = "Review Vote"
        verbose_name_plural = "Review Votes"

    def __unicode__(self):
        vote_type = "Kudos" if self.is_kudos else "Dislike"
        return "{} for review {} by {}".format(
            vote_type,
            self.review.id,
            self.user.username,
        )
