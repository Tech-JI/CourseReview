from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Count
from .models import Course, Review, Vote
from .serializers import CourseSerializer, ReviewSerializer, VoteSerializer
from lib import constants


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=["get"])
    def reviews(self, request, pk=None):
        course = self.get_object()
        reviews = course.review_set.all().order_by("-term")
        page = self.paginate_queryset(reviews)
        serializer = ReviewSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"])
    def medians(self, request, pk=None):
        course = self.get_object()
        medians = course.coursemedian_set.all()
        data = {
            "medians": [
                {
                    "term": m.term,
                    "median": m.median,
                    "enrollment": m.enrollment,
                    "section": m.section,
                }
                for m in medians
            ]
        }
        return Response(data)

    @action(detail=True, methods=["post"])
    def vote(self, request, pk=None):
        course = self.get_object()
        serializer = VoteSerializer(data=request.data)
        if serializer.is_valid():
            vote = serializer.save(course=course, user=request.user)
            return Response({"status": "vote recorded"})
        else:
            return Response(serializer.errors, status=400)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        course = get_object_or_404(Course, id=self.request.data["course_id"])
        serializer.save(user=self.request.user, course=course)


class VoteViewSet(viewsets.ModelViewSet):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        course = get_object_or_404(Course, id=self.request.data["course_id"])
        serializer.save(user=self.request.user, course=course)
