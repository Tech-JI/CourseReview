from django.test import TestCase

from apps.web.models import Vote
from apps.web.tests import factories
from lib import constants


class StudentTestCase(TestCase):
    def test_can_see_recommendations(self):
        s = factories.StudentFactory()
        self.assertFalse(s.can_see_recommendations())

        # create sufficient votes of wrong type
        for _ in range(constants.REC_UPVOTE_REQ):
            factories.VoteFactory(
                user=s.user, category=Vote.CATEGORIES.DIFFICULTY, value=1
            )
            for value in [-1, 0]:
                for category in [c[0] for c in Vote.CATEGORIES.CHOICES]:
                    factories.VoteFactory(user=s.user, category=category, value=value)

        # cannot view if does not reach vote count
        Vote.objects.all().delete()
        factories.ReviewFactory(user=s.user)
        for _ in range(constants.REC_UPVOTE_REQ - 1):
            factories.VoteFactory(
                user=s.user, category=Vote.CATEGORIES.QUALITY, value=1
            )
            self.assertFalse(s.can_see_recommendations())

        # can view
        factories.VoteFactory(user=s.user, category=Vote.CATEGORIES.QUALITY, value=1)
        self.assertTrue(s.can_see_recommendations())
