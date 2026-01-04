import factory
from django.contrib.auth.models import User
import factory.fuzzy
from apps.web import models
from lib import constants
from apps.web.models.course import Course
from apps.web.models.student import Student


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("first_name")
    email = factory.Faker("email")
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


# class CourseFactory(factory.django.DjangoModelFactory):
#    class Meta:
#        model = models.Course


# course_title = factory.Faker("words")
# department = "COSC"
# number = factory.Faker("random_number")
# url = factory.Faker("url")
# description = factory.Faker("text")
class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course  # or models.Course

    # 1. Title using Faker to generate random words
    course_title = factory.Faker("sentence", nb_words=3)

    # 2. Department (defaults to MATH, can be overridden)
    department = "MATH"

    # 3. Number sequence (starts from 100, 101, 102...)
    number = factory.Sequence(lambda n: 100 + n)

    # 4. Construct unique course_code in JI style (e.g., MATH100, MATH101)
    # This prevents the "UniqueViolation" error
    @factory.lazy_attribute
    def course_code(self):
        return f"{self.department}{self.number}"

    url = factory.Faker("url")
    description = factory.Faker("paragraph")


class CourseOfferingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CourseOffering

    course = factory.SubFactory(CourseFactory)
    term = "2023F"
    period = "2A"  # Common period format


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Review

    course = factory.SubFactory(CourseFactory)
    user = factory.SubFactory(UserFactory)

    professor = factory.Faker("name")
    term = constants.CURRENT_TERM
    comments = factory.Faker("paragraph")


class DistributiveRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DistributiveRequirement

    name = "ART"
    distributive_type = models.DistributiveRequirement.DISTRIBUTIVE


class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Student

    user = factory.SubFactory(UserFactory)


#    confirmation_link = factory.LazyFunction(lambda: get_random_string(length=16))


class VoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Vote

    value = 0
    course = factory.SubFactory(CourseFactory)
    user = factory.SubFactory(UserFactory)
    category = models.Vote.CATEGORIES.QUALITY
