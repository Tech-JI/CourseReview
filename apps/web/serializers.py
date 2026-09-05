# apps/web/serializers.py
from django.conf import settings
from django.db.models import Count
from rest_framework import serializers

from apps.web.models import (
    Course,
    CourseOffering,
    DistributiveRequirement,
    Instructor,
    Review,
    Syllabus,
    SyllabusFile,
    Vote,
)
from lib import constants
from lib.terms import is_valid_term, normalize_term


class DistributiveRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DistributiveRequirement
        fields = ("name",)


class CourseOfferingSerializer(serializers.ModelSerializer):
    instructors = serializers.StringRelatedField(many=True)  # Use names

    class Meta:
        model = CourseOffering
        fields = ("term", "section", "period", "limit", "instructors")


class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = ("id", "name")


class SyllabusFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyllabusFile
        fields = ("id", "original_filename", "size", "content_type")


class SyllabusSerializer(serializers.ModelSerializer):
    instructor = InstructorSerializer(read_only=True)
    file = SyllabusFileSerializer(read_only=True)
    uploaded_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Syllabus
        fields = (
            "id",
            "course",
            "instructor",
            "file",
            "uploaded_by",
            "status",
            "summary_md",
            "verdict",
            "comparison",
            "is_primary",
            "error_message",
            "created_at",
            "updated_at",
        )


class SyllabusCreateSerializer(serializers.Serializer):
    file = serializers.FileField()
    instructor = serializers.IntegerField()

    def validate_file(self, value):
        allowed = settings.SYLLABUS["ALLOWED_EXTENSIONS"]
        name = value.name.lower()
        if not any(name.endswith(ext) for ext in allowed):
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed: {', '.join(allowed)}"
            )
        if value.size > settings.SYLLABUS["MAX_UPLOAD_SIZE"]:
            raise serializers.ValidationError("File exceeds the 20 MB upload limit")
        return value

    def validate_instructor(self, value):
        course = self.context["course"]
        teaches = Instructor.objects.filter(
            courseoffering__course=course, pk=value
        ).exists()
        if not teaches:
            raise serializers.ValidationError("Instructor does not teach this course")
        return value


class SyllabusAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syllabus
        fields = ("summary_md", "verdict", "comparison", "is_primary")
        read_only_fields = ("comparison",)


class ReviewSerializer(serializers.ModelSerializer):
    #    user = serializers.StringRelatedField()
    term = serializers.CharField()
    professor = serializers.CharField()
    user_vote = serializers.SerializerMethodField()
    kudos_count = serializers.SerializerMethodField()
    dislike_count = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            "id",
            # don't return the author of this review
            #            "user",
            "term",
            "professor",
            "comments",
            "kudos_count",
            "dislike_count",
            "created_at",
            "user_vote",
        )
        read_only_fields = (
            "id",
            "kudos_count",
            "dislike_count",
            "created_at",
            "user_vote",
        )

    def get_kudos_count(self, obj):
        """Get the number of kudos for this review"""
        return getattr(obj, "kudos_count", 0)

    def get_dislike_count(self, obj):
        """Get the number of dislikes for this review"""
        return getattr(obj, "dislike_count", 0)

    def get_user_vote(self, obj):
        """Get the current user's vote for this review"""
        return getattr(obj, "user_vote", None)

    def validate_term(self, value):
        """Validate term format"""
        term = normalize_term(value)

        if term and is_valid_term(term):
            return term
        else:
            raise serializers.ValidationError(
                "Please use a valid term, e.g. {}".format(constants.CURRENT_TERM)
            )

    def validate_professor(self, value):
        """Validate professor name format"""
        names = value.split(" ")

        if len(names) < 2:
            raise serializers.ValidationError(
                "Please use a valid professor name, e.g. John Smith"
            )

        return " ".join([n.capitalize() for n in names])

    def validate_comments(self, value):
        """Validate review minimum length"""
        REVIEW_MINIMUM_LENGTH = settings.WEB["REVIEW"]["COMMENT_MIN_LENGTH"]

        if len(value) < REVIEW_MINIMUM_LENGTH:
            raise serializers.ValidationError(
                "Please write a longer review (at least {} characters)".format(
                    REVIEW_MINIMUM_LENGTH
                )
            )

        return value


class DepartmentSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    count = serializers.IntegerField()


class CourseSearchSerializer(serializers.ModelSerializer):
    distribs = DistributiveRequirementSerializer(many=True, read_only=True)
    review_count = serializers.SerializerMethodField()
    is_offered_in_current_term = serializers.SerializerMethodField()
    instructors = serializers.SerializerMethodField()
    quality_score = serializers.SerializerMethodField()
    difficulty_score = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "course_code",
            "course_title",
            "distribs",
            "review_count",
            "quality_score",
            "difficulty_score",
            "last_offered",
            "is_offered_in_current_term",
            "instructors",
        )

    def get_review_count(self, obj):
        return getattr(obj, "review_count", obj.review_set.count())

    def get_quality_score(self, obj):
        return getattr(obj, "quality_score", 0.0)

    def get_difficulty_score(self, obj):
        return getattr(obj, "difficulty_score", 0.0)

    def get_is_offered_in_current_term(self, obj):
        return obj.courseoffering_set.filter(term=constants.CURRENT_TERM).exists()

    def get_instructors(self, obj):
        """Return a list of instructor names for the course"""
        instructors = obj.get_instructors()
        return [instructor.name for instructor in instructors]

    def get_short_description(self, obj):
        """Return a shortened version of the course description"""
        if obj.description:
            return (
                obj.description
                if len(obj.description) <= 300
                else obj.description[:300] + "..."
            )
        return None

    def get_offered_times_string(self, obj):
        """Return a string of when the course is offered"""
        periods = set(o.period for o in obj.courseoffering_set.all())
        return ", ".join(periods) if periods else None

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")

        # Remove scores for unauthenticated users
        if not request or not request.user.is_authenticated:
            ret.pop("quality_score", None)
            ret.pop("difficulty_score", None)

        # Add summary fields
        ret["short_description"] = self.get_short_description(instance)
        ret["offered_times_string"] = self.get_offered_times_string(instance)

        return ret


class CourseVoteSerializer(serializers.Serializer):
    value = serializers.IntegerField(min_value=1, max_value=5)
    forLayup = serializers.BooleanField()


class ReviewVoteSerializer(serializers.Serializer):
    is_kudos = serializers.BooleanField()


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
    instructors = serializers.SerializerMethodField()
    course_topics = serializers.SerializerMethodField()
    quality_vote_count = serializers.SerializerMethodField()
    difficulty_vote_count = serializers.SerializerMethodField()
    quality_score = serializers.SerializerMethodField()
    difficulty_score = serializers.SerializerMethodField()

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
            "quality_vote_count",
            "difficulty_vote_count",
            "last_offered",
            "professors_and_review_count",
            "difficulty_vote",
            "quality_vote",
            "can_write_review",
            "instructors",
            "course_topics",
        )

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")

        # Remove scores and votes for unauthenticated users
        if not request or not request.user.is_authenticated:
            ret.pop("quality_score", None)
            ret.pop("difficulty_score", None)
            ret.pop("difficulty_vote", None)
            ret.pop("quality_vote", None)
            ret.pop("quality_vote_count", None)
            ret.pop("difficulty_vote_count", None)

        return ret

    def get_review_set(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            sort_by = request.query_params.get("review_sort_by", "term")
            if sort_by == "professor":
                queryset = obj.review_set.order_by("professor")
            else:
                queryset = obj.review_set.order_by("-term")
            return ReviewSerializer(queryset, many=True, context=self.context).data
        return []

    def get_review_count(self, obj):
        return getattr(obj, "review_count", obj.review_set.count())

    def get_quality_score(self, obj):
        return getattr(obj, "quality_score", 0.0)

    def get_difficulty_score(self, obj):
        return getattr(obj, "difficulty_score", 0.0)

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
            if vote and vote.value > 0:
                return {"value": vote.value}
        return None

    def get_quality_vote(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            _, vote = Vote.objects.for_course_and_user(obj, request.user)
            if vote and vote.value > 0:
                return {"value": vote.value}
        return None

    def get_quality_vote_count(self, obj):
        return getattr(
            obj, "quality_vote_count", Vote.objects.get_vote_count(obj, "quality")
        )

    def get_difficulty_vote_count(self, obj):
        return getattr(
            obj, "difficulty_vote_count", Vote.objects.get_vote_count(obj, "difficulty")
        )

    def get_can_write_review(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Review.objects.user_can_write_review(request.user.id, obj.id)
        return False

    def get_instructors(self, obj):
        """Return instructor {id, name} pairs so clients can key uploads on them.

        Term-agnostic: a syllabus can exist for any instructor who ever taught
        the course, and uploads should not be blocked by term bookkeeping.
        """
        instructors = obj.get_instructors(term=None)
        return [{"id": i.id, "name": i.name} for i in instructors]

    def get_course_topics(self, obj):
        return obj.course_topics
