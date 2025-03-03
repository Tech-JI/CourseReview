# apps/web/serializers.py
from django.db.models import Count
from rest_framework import serializers

from apps.web.models import (
    Course,
    CourseMedian,
    CourseOffering,
    DistributiveRequirement,
    Instructor,
    Review,
    Vote,
)
from lib.departments import get_department_name


class DistributiveRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DistributiveRequirement
        fields = ("name",)


class CourseOfferingSerializer(serializers.ModelSerializer):
    instructors = serializers.StringRelatedField(many=True)  # Use names

    class Meta:
        model = CourseOffering
        fields = ("term", "section", "period", "limit", "instructors")


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()  # Display username
    term = serializers.CharField()
    professor = serializers.CharField()

    class Meta:
        model = Review
        fields = ("id", "user", "term", "professor", "comments", "created_at")


class DepartmentSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    count = serializers.IntegerField()


class CourseSerializer(serializers.ModelSerializer):
    review_set = serializers.SerializerMethodField()
    courseoffering_set = CourseOfferingSerializer(many=True, read_only=True)
    distribs = DistributiveRequirementSerializer(many=True, read_only=True)
    xlist = serializers.SerializerMethodField()
    professors_and_review_count = serializers.SerializerMethodField()
    last_offered = serializers.CharField()
    difficulty_vote = serializers.SerializerMethodField()
    quality_vote = serializers.SerializerMethodField()
    can_write_review = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "course_code",
            "course_title",
            "department",
            "number",
            "description",
            "distribs",
            "xlist",
            "review_set",
            "review_count",
            "courseoffering_set",
            "difficulty_score",
            "quality_score",
            "last_offered",
            "professors_and_review_count",
            "difficulty_vote",
            "quality_vote",
            "can_write_review",
        )

    def get_review_set(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return ReviewSerializer(obj.review_set.all(), many=True).data
        return []

    def get_review_count(self, obj):
        return obj.review_set.count()

    def get_xlist(self, obj):
        return [
            {"short_name": c.short_name(), "id": c.id}
            for c in obj.crosslisted_courses.all()
        ]

    def get_professors_and_review_count(self, obj):
        professors_and_review_count = list(
            obj.review_set.values("professor")
            .annotate(Count("professor"))
            .order_by("-professor__count")
            .values_list("professor", "professor__count")
        )

        # Get instructor names based on instrutors parsed from course offerings
        professors_and_review_count += [
            (instructor_name, 0)
            for instructor_name in Instructor.objects.filter(
                courseoffering__course=obj,
            )
            .exclude(
                name__in=[professor for professor, _ in professors_and_review_count],
            )
            .values_list("name", flat=True)
            .distinct()
        ]
        return professors_and_review_count

    def get_difficulty_vote(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            vote, _ = Vote.objects.for_course_and_user(obj, request.user)
            if vote:
                return {
                    "value": vote.value,
                    "is_upvote": vote.is_upvote(),
                    "is_downvote": vote.is_downvote(),
                }
        return None

    def get_quality_vote(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            _, vote = Vote.objects.for_course_and_user(obj, request.user)
            if vote:
                return {
                    "value": vote.value,
                    "is_upvote": vote.is_upvote(),
                    "is_downvote": vote.is_downvote(),
                }
        return None

    def get_can_write_review(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Review.objects.user_can_write_review(request.user.id, obj.id)
        return False
