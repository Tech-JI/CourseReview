import hashlib

import factory
import factory.fuzzy
from django.contrib.auth.models import User

# Import models from their individual files
from apps.web.models.course import Course
from apps.web.models.course_offering import CourseOffering
from apps.web.models.instructor import Instructor
from apps.web.models.review import Review
from apps.web.models.student import Student
from apps.web.models.syllabus import Syllabus
from apps.web.models.syllabus_file import SyllabusFile


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Ensure password is hashed correctly so auth_client can log in"""
        password = kwargs.pop("password", "password123")
        obj = model_class(*args, **kwargs)
        obj.set_password(password)
        obj.save()
        return obj


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    course_title = factory.Faker("sentence", nb_words=3)
    department = factory.fuzzy.FuzzyChoice(["MATH", "PHYS", "EECS"])
    number = factory.Sequence(lambda n: 100 + n)

    @factory.lazy_attribute
    def course_code(self):
        """Generates unique MATH100, PHYS101, etc."""
        return f"{self.department}{str(self.number):<04}J"

    description = factory.Faker("paragraph")


class CourseOfferingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseOffering

    course = factory.SubFactory(CourseFactory)
    term = "23F"
    section = factory.Sequence(lambda n: n)
    period = "2A"


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    course = factory.SubFactory(CourseFactory)
    user = factory.SubFactory(UserFactory)

    term = "23F"
    professor = factory.Faker("name")
    comments = factory.Faker("paragraph")


class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Student

    user = factory.SubFactory(UserFactory)


class DistributiveRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        # Using string reference for potential distributive requirements model
        model = "web.DistributiveRequirement"

    name = factory.Sequence(lambda n: f"Dist{n}")


class InstructorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Instructor

    name = factory.Sequence(lambda n: f"Prof{n} Name{n}")


def syllabus_pdf_bytes(seed: str = "syllabus") -> bytes:
    """Minimal valid-enough PDF bytes; distinct seed => distinct sha256."""
    return (
        f"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Info {seed}>>\n%%EOF"
    ).encode()


class SyllabusFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SyllabusFile

    content_type = "application/pdf"
    original_filename = factory.Sequence(lambda n: f"syllabus-{n}.pdf")
    # Unique per created file (unique sha256 constraint). Content hash
    # consistency is the upload view's job, not the factory's.
    sha256 = factory.Sequence(
        lambda n: hashlib.sha256(f"factory-seed-{n}".encode()).hexdigest()
    )
    size = factory.LazyFunction(lambda: len(syllabus_pdf_bytes()))
    file = factory.django.FileField(data=syllabus_pdf_bytes(), filename="syllabus.pdf")


class SyllabusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Syllabus

    course = factory.SubFactory(CourseFactory)
    instructor = factory.SubFactory(InstructorFactory)
    file = factory.SubFactory(SyllabusFileFactory)
    status = Syllabus.Status.ANALYZED
    summary_md = "# Syllabus\n\nGrading: 40% homework, 60% final."
    verdict = {
        "match_score": 90,
        "matches_course_content": True,
        "is_legitimate": True,
        "flags": [],
    }
