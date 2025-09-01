from __future__ import unicode_literals

import re

from django.db import models
from django.db.models import Q
from django.urls import reverse

from lib.constants import CURRENT_TERM
from lib.terms import numeric_value_of_term

from .course_offering import CourseOffering


class CourseManager(models.Manager):
    course_search_regex = re.compile(
        r"^(?P<department_or_query>\D*)(?P<number>\d*)" "(?P<other>.*)"
    )
    DEPARTMENT_LENGTHS = [2, 3, 4]

    def for_term(self, term, dist=None):
        query = self.filter(id__in=CourseOffering.objects.course_ids_for_term(term))
        if dist:
            query = query.filter(distribs__name=dist)
        return query

    def search(self, query):
        query_data = {
            k: v.strip()
            for k, v in self.course_search_regex.match(query).groupdict().items()
        }

        department_or_query = query_data["department_or_query"]
        number = query_data["number"]
        # subnumber = query_data["subnumber"]
        # other = query_data["other"]

        if not department_or_query:
            return self.none()
        elif len(department_or_query) not in self.DEPARTMENT_LENGTHS:
            # must be query, too long to be department. ignore numbers we may
            # have. e.g. "Introduction"
            return Course.objects.filter(title__icontains=department_or_query)
        # elif number and subnumber:
        #     # course with number and subnumber
        #     # e.g. COSC 089.01
        #     return Course.objects.filter(
        #         department__iexact=department_or_query,
        #         number=number,
        #         subnumber=subnumber)
        elif number:
            # course with number, could be ambiguous
            # e.g. COSC 001
            return Course.objects.filter(
                department__iexact=department_or_query, number=number
            )
        else:
            # could be either department or query
            # e.g. "COSC" (department) or "War" (query)
            # courses = Course.objects.filter(
            #     department__iexact=department_or_query, ).order_by(
            #         "number", "subnumber")
            courses = Course.objects.filter(
                department__iexact=department_or_query
            ).order_by("number")
            if len(courses) == 0:
                return Course.objects.filter(
                    course_title__icontains=department_or_query
                )
            return courses


class Course(models.Model):
    objects = CourseManager()

    crosslisted_courses = models.ManyToManyField("self", blank=True)
    distribs = models.ManyToManyField("DistributiveRequirement", blank=True)

    class SOURCES:
        ORC = "ORC"
        TIMETABLE = "TIMETABLE"
        CHOICES = (
            (ORC, "Organization, Regulations, and Courses"),
            (TIMETABLE, "Academic Timetable"),
        )

    course_code = models.CharField(
        max_length=10, unique=True, db_index=True, default=""
    )  # Avoid two empty types of blank and null
    course_title = models.CharField(max_length=100, default="")
    department = models.CharField(max_length=5, db_index=True, default="")
    number = models.IntegerField(null=True, blank=True, db_index=True)
    course_credits = models.IntegerField(null=True, blank=True)
    pre_requisites = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    course_topics = models.JSONField(null=True, blank=True)
    url = models.URLField(null=True, blank=True, max_length=400)
    # number = models.IntegerField(db_index=True)
    # subnumber = models.IntegerField(null=True, db_index=True, blank=True)
    # source = models.CharField(max_length=16, choices=SOURCES.CHOICES)

    difficulty_score = models.FloatField(default=0.0)
    quality_score = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course_code"], name="unique_course_code")
        ]

    def __unicode__(self):
        return "{}: {}".format(self.short_name(), self.title)

    def get_absolute_url(self):
        return reverse("course_detail", args=[self.id])

    def short_name(self):
        return "{0}{1:03d}".format(self.department, self.number)

    def distribs_string(self, separator=", "):
        return separator.join([d.name for d in self.distribs.all()])

    def offered_times_string(self, term=CURRENT_TERM):
        return ", ".join(self.offered_times(term))

    def offered_times(self, term=CURRENT_TERM):
        offered_times = []

        # filtering here creates an N+1 query... so we filter it ourselves.
        # N+1 occurs on current_term page, as CourseOffering preloading is
        # ignored if a filter is added here
        all_course_offerings = self.courseoffering_set.all()
        term_course_offerings = []
        for offering in all_course_offerings:
            if offering.term == term:
                term_course_offerings.append(offering)

        for offering in term_course_offerings:
            if len(offering.period) <= 3:
                offered_times.append(offering.period)

        some_times_redacted = len(term_course_offerings) != len(offered_times)
        offered_times = list(set(offered_times))
        if some_times_redacted:
            offered_times.append("other")
        return offered_times

    def is_offered(self, term=CURRENT_TERM):
        return self.courseoffering_set.filter(term=term).count() > 0

    def prefetched_is_offered(self, term=CURRENT_TERM):
        for offering in self.courseoffering_set.all():
            if offering.term == term:
                return True
        return False

    def last_offered(self):
        last_offering = self.courseoffering_set.last()
        if last_offering:
            return last_offering.term
        else:
            max_value_term = None
            max_value = 0
            for term in self.coursemedian_set.values_list("term", flat=True):
                value = numeric_value_of_term(term)
                if value > max_value:
                    max_value_term = term
                    max_value = value
            return max_value_term

    def short_description(self):
        if self.description:
            return ". ".join(self.description.split(". ")[:2]) + "..."

    def search_reviews(self, query):
        return self.review_set.order_by("-term").filter(
            Q(comments__icontains=query) | Q(professor__icontains=query)
        )

    def should_ask_viewers_to_contribute(self):
        return self.department in {"COSC", "ENGS"}

    def get_instructors(self, term=CURRENT_TERM):
        """
        Get all instructors for this course in the specified term.
        If term is None, returns instructors across all terms.
        """
        instructors = []
        offerings = self.courseoffering_set.all()

        if term:
            offerings = offerings.filter(term=term)

        for offering in offerings:
            for instructor in offering.instructors.all():
                instructors.append(instructor)

        # Remove duplicates while preserving order
        unique_instructors = []
        seen = set()
        for instructor in instructors:
            if instructor.id not in seen:
                seen.add(instructor.id)
                unique_instructors.append(instructor)

        return unique_instructors
