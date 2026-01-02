import factory
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from apps.web import models
from lib import constants
from apps.web.models import Course, Review
import factory.fuzzy


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True

    @classmethod
    def _prepare(cls, create, **kwargs):
        # thanks: https://gist.github.com/mbrochh/2433411
        password = factory.Faker("password")
        if "password" in kwargs:
            password = kwargs.pop("password")
        user = super(UserFactory, cls)._prepare(create, **kwargs)
        user.set_password(password)
        if create:
            user.save()
        return user


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    # in line with the real name you searched
    course_title = factory.Faker("sentence", nb_words=3)
    course_code = factory.Sequence(lambda n: f"JI-CS{100 + n}")
    department = factory.fuzzy.FuzzyChoice(["UMJI", "EECS", "MATH"])
    number = factory.Sequence(lambda n: 100 + n)

    # create fake data
    description = factory.Faker("paragraph")
    course_credits = 4


class CourseOfferingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CourseOffering

    course = factory.SubFactory(CourseFactory)

    term = constants.CURRENT_TERM
    section = factory.Faker("random_number")
    period = "2A"


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    # connect to the previous factory厂
    course = factory.SubFactory(CourseFactory)
    user = factory.SubFactory(UserFactory)

    professor = factory.Faker("name")
    comments = factory.Faker("paragraph")
    term = "2023-Fall"

    # assume having evaluation
    # rating = fuzzy.FuzzyInteger(1, 5)


class DistributiveRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DistributiveRequirement

    name = "ART"
    distributive_type = models.DistributiveRequirement.DISTRIBUTIVE


class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Student

    user = factory.SubFactory(UserFactory)
    confirmation_link = get_random_string(length=16)


class VoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Vote

    value = 0
    course = factory.SubFactory(CourseFactory)
    user = factory.SubFactory(UserFactory)
    category = models.Vote.CATEGORIES.QUALITY
