from apps.web.models import (
    Course,
    CourseMedian,
    Instructor,
    Review,
    ReviewVote,
    Vote,
)

from apps.web.models.forms import ReviewForm

from apps.web.serializers import (
    CourseSearchSerializer,
    CourseSerializer,
    ReviewSerializer,
)

from lib import constants
from lib.departments import get_department_name
from lib.grades import numeric_value_for_grade
from lib.terms import numeric_value_of_term


import logging

from django.db.models import Count
from django.conf import settings
from rest_framework import generics, mixins, pagination, status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class CoursesPagination(pagination.PageNumberPagination):
    page_size = settings.DEFAULTS["WEB"]["COURSE"]["PAGE_SIZE"]


@api_view(["GET"])
def user_status(request):
    if request.user.is_authenticated:
        logger.info("User is authenticated")
        return Response({"isAuthenticated": True, "username": request.user.username})
    else:
        logger.info("User is not authenticated")
        return Response({"isAuthenticated": False})


@api_view(["GET"])
@permission_classes([AllowAny])
def landing_api(request):
    """API endpoint for landing page data"""
    return Response(
        {
            "review_count": Review.objects.count(),
        }
    )


class CoursesListAPI(generics.GenericAPIView, mixins.ListModelMixin):
    """API endpoint for listing courses with filtering, sorting, and pagination."""

    serializer_class = CourseSearchSerializer
    permission_classes = [AllowAny]
    pagination_class = CoursesPagination

    def get_queryset(self):
        queryset = Course.objects.all().prefetch_related("distribs", "review_set")
        queryset = queryset.annotate(num_reviews=Count("review"))
        return queryset

    def _filter_courses(self, queryset):
        """Helper function to apply all filters to courses queryset."""
        department = self.request.query_params.get("department")
        if department:
            queryset = queryset.filter(department__iexact=department)

        code = self.request.query_params.get("code")
        if code:
            queryset = queryset.filter(course_code__icontains=code)

        queryset = self._filter_by_score_params(queryset)
        return queryset

    def _filter_by_score_params(self, queryset):
        """Helper function to filter by quality and difficulty score parameters."""
        if not self.request.user.is_authenticated:
            return queryset

        query_param_mapping = [
            ("min_quality", "quality_score"),
            ("min_difficulty", "difficulty_score"),
        ]

        for param_name, field_name in query_param_mapping:
            param_value = self.request.query_params.get(param_name)
            if param_value:
                try:
                    threshold = int(param_value)
                    queryset = queryset.filter(**{f"{field_name}__gte": threshold})
                except (ValueError, TypeError):
                    pass
        return queryset

    def _sort_courses(self, queryset):
        """Helper function to sort courses based on request parameters."""
        sort_by = self.request.query_params.get("sort_by", "course_code")
        sort_order = self.request.query_params.get("sort_order", "asc")
        sort_prefix = "-" if sort_order.lower() == "desc" else ""

        allowed_sort_fields = ["course_code", "num_reviews"]
        if self.request.user.is_authenticated:
            allowed_sort_fields.extend(["quality_score", "difficulty_score"])

        sort_field = sort_by if sort_by in allowed_sort_fields else "course_code"
        return queryset.order_by(f"{sort_prefix}{sort_field}")

    def filter_queryset(self, queryset):
        """Override to apply both filtering and sorting."""
        queryset = self._filter_courses(queryset)
        queryset = self._sort_courses(queryset)
        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CourseDetailAPI(generics.GenericAPIView, mixins.RetrieveModelMixin):
    """API endpoint for retrieving course details."""

    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    queryset = Course.objects.all()

    def get_object(self):
        course_id = self.kwargs.get("course_id")
        try:
            return Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            logger.warning(f"Course with id {course_id} does not exist")
            return None

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class CourseReviewAPI(generics.GenericAPIView):
    """API endpoint for course reviews - GET (search), POST (create), DELETE (delete)."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Course.objects.all()

    def get_object(self):
        """Get course object for review operations."""
        course_id = self.kwargs.get("course_id")
        try:
            return Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            logger.warning(f"Course with id {course_id} does not exist")
            return None

    def get(self, request, *args, **kwargs):
        """Search reviews for a course."""
        course = self.get_object()
        if course is None:
            return Response({"detail": "Course not found"}, status=404)

        query = request.GET.get("q", "").strip()
        reviews = course.search_reviews(query)
        review_count = reviews.count()

        serializer = ReviewSerializer(reviews, many=True, context={"request": request})

        return Response(
            {
                "query": query,
                "course_id": course.id,
                "course_short_name": course.short_name(),
                "reviews_full_count": review_count,
                "remaining": 0,  # No remaining since user is authenticated
                "reviews": serializer.data,
            }
        )

    def post(self, request, *args, **kwargs):
        """Create a new review for a course."""
        course = self.get_object()
        if course is None:
            return Response({"detail": "Course not found"}, status=404)

        if not Review.objects.user_can_write_review(request.user.id, course.id):
            logger.warning(
                f"User {request.user.id} cannot write review for course {course.id}"
            )
            return Response({"detail": "User cannot write review"}, status=403)

        form = ReviewForm(request.data)
        if form.is_valid():
            review = form.save(commit=False)
            review.course = course
            review.user = request.user
            review.save()
            serializer = CourseSerializer(course, context={"request": request})
            return Response(serializer.data, status=201)

        logger.warning(f"Review form errors: {form.errors}")
        return Response(form.errors, status=400)

    def delete(self, request, *args, **kwargs):
        """Delete user's review for a course."""
        course = self.get_object()
        if course is None:
            return Response({"detail": "Course not found"}, status=404)

        Review.objects.delete_reviews_for_user_course(user=request.user, course=course)
        serializer = CourseSerializer(course, context={"request": request})
        return Response(serializer.data, status=200)


@api_view(["GET"])
@permission_classes([AllowAny])
def departments_api(request):
    department_codes_and_counts = (
        Course.objects.values("department")
        .annotate(Count("department"))
        .order_by("department")
        .values_list("department", "department__count")
    )

    departments_data = [
        {"code": code, "name": get_department_name(code), "count": count}
        for code, count in department_codes_and_counts
    ]

    return Response(departments_data)


@api_view(["GET"])
def medians(request, course_id):
    # retrieve course medians for term, and group by term for averaging
    medians_by_term = {}
    for course_median in CourseMedian.objects.filter(course=course_id):
        if course_median.term not in medians_by_term:
            medians_by_term[course_median.term] = []

        medians_by_term[course_median.term].append(
            {
                "median": course_median.median,
                "enrollment": course_median.enrollment,
                "section": course_median.section,
                "numeric_value": numeric_value_for_grade(course_median.median),
            }
        )

    return Response(
        {
            "medians": sorted(
                [
                    {
                        "term": term,
                        "avg_numeric_value": sum(
                            m["numeric_value"] for m in term_medians
                        )
                        / len(term_medians),
                        "courses": term_medians,
                    }
                    for term, term_medians in medians_by_term.items()
                ],
                key=lambda x: numeric_value_of_term(x["term"]),
                reverse=True,
            )
        },
        status=200,
    )


@api_view(["GET"])
def course_professors(request, course_id):
    return Response(
        {
            "professors": sorted(
                set(
                    Review.objects.filter(course=course_id)
                    .values_list("professor", flat=True)
                    .distinct()
                )
                | set(
                    Instructor.objects.filter(
                        courseoffering__course=course_id,
                    )
                    .values_list("name", flat=True)
                    .distinct()
                )
            )
        },
        status=200,
    )


@api_view(["GET"])
def course_instructors(request, course_id):
    try:
        course = Course.objects.get(pk=course_id)
        instructors = course.get_instructors()
        return Response(
            {"instructors": [instructor.name for instructor in instructors]}, status=200
        )
    except Course.DoesNotExist:
        logger.warning(f"Course with id {course_id} not found for instructors API")
        return Response({"error": "Course not found"}, status=404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def course_vote_api(request, course_id):
    try:
        value = request.data["value"]
        forLayup = request.data["forLayup"]
    except KeyError:
        logger.warning(
            f"Missing required fields in course vote API for course {course_id}"
        )
        return Response(
            {"detail": "Missing required fields: value, forLayup"}, status=400
        )

    category = Vote.CATEGORIES.DIFFICULTY if forLayup else Vote.CATEGORIES.QUALITY
    new_score, is_unvote, new_vote_count = Vote.objects.vote(
        int(value), course_id, category, request.user
    )

    return Response(
        {
            "new_score": new_score,
            "was_unvote": is_unvote,
            "new_vote_count": new_vote_count,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def review_vote_api(request, review_id):
    """
    API endpoint for voting on reviews (kudos/dislike).

    URL: /api/review/{review_id}/vote/
    POST data:
    - is_kudos: boolean (True for kudos, False for dislike)

    Returns:
    - kudos_count: updated kudos count
    - dislike_count: updated dislike count
    - user_vote: user's current vote (True/False/None)
    """

    try:
        is_kudos = request.data.get("is_kudos")

        if is_kudos is None:
            logger.warning("is_kudos field is required for review vote API")
            return Response({"detail": "is_kudos field is required"}, status=400)

        is_kudos = bool(is_kudos)

        # Use the ReviewVoteManager's vote method
        kudos_count, dislike_count, user_vote = ReviewVote.objects.vote(
            review_id=review_id, user=request.user, is_kudos=is_kudos
        )

        if kudos_count is None or dislike_count is None:
            # Review doesn't exist
            logger.warning(f"Review {review_id} not found for voting")
            return Response({"detail": "Review not found"}, status=404)

        return Response(
            {
                "kudos_count": kudos_count,
                "dislike_count": dislike_count,
                "user_vote": user_vote,
            }
        )

    except Exception:
        return Response(
            {"detail": "An error occurred processing your request"},
            status=500,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_review_api(request, course_id):
    """
    API endpoint to get the authenticated user's review for a specific course.

    Returns:
    - Review data if the user has written a review for this course
    - 404 if no review found
    - 403 if user is not authenticated
    """

    try:
        # Get the course
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            logger.warning(f"Course {course_id} not found for get_user_review_api")
            return Response({"detail": "Course not found"}, status=404)

        # Get the user's review for this course
        review = Review.objects.get_user_review_for_course(request.user, course)

        if review is None:
            logger.info(
                f"No user review found for course {course_id} and user {request.user}"
            )
            return Response(
                {"detail": "No user review found for this course"}, status=404
            )

        # Serialize and return the review
        serializer = ReviewSerializer(review)
        return Response(serializer.data)

    except Exception:
        return Response(
            {"detail": "An error occurred processing your request"},
            status=500,
        )
