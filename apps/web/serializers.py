from rest_framework import serializers
from apps.web.models import Course, Review, Vote


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            "id",
            "course_code",
            "course_title",
            "department",
            "number",
            "description",
            "quality_score",
            "difficulty_score",
            "distribs_string",
            "offered_times_string",
            "is_offered",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "course", "professor", "term", "comments", "created_at"]
        read_only_fields = ["user"]


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ["id", "course", "value", "category"]
        read_only_fields = ["user"]
