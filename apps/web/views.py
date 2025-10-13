from apps.web.models import (
    Course,
    CourseMedian,
    Instructor,
    Review,
    ReviewVote,
    Vote,
)


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

    def _filter(self, queryset):
        """filter courses and filter by score."""
        queryset = self._filter_courses(queryset)
        queryset = self._filter_by_score(queryset)
        return queryset

    def _filter_courses(self, queryset):
        """Helper function to apply all filters to courses queryset."""
        department = self.request.query_params.get("department")
        code = self.request.query_params.get("code")
        if department:
            queryset = queryset.filter(department__iexact=department)
        if code:
            queryset = queryset.filter(course_code__icontains=code)
        return queryset

    def _filter_by_score(self, queryset):
        """Helper function to filter by quality and difficulty score."""
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

    def _sort(self, queryset):
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
        queryset = self._filter(queryset)
        queryset = self._sort(queryset)
        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CoursesDetailAPI(generics.GenericAPIView, mixins.RetrieveModelMixin):
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


class CoursesReviewsAPI(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.CreateModelMixin
):
    """API endpoint for course reviews - GET (list/search), POST (create)."""

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get reviews for the specified course."""
        course_id = self.kwargs.get("course_id")
        try:
            course = Course.objects.get(id=course_id)
            return Review.objects.filter(course=course)
        except Course.DoesNotExist:
            logger.warning(f"Course with id {course_id} does not exist")
            return Review.objects.none()

    def list(self, request, *args, **kwargs):
        """List reviews with optional filtering."""
        queryset = self.get_queryset()

        # Handle all query parameters here
        query = request.query_params.get("q", "").strip()
        if query:
            course_id = self.kwargs.get("course_id")
            try:
                course = Course.objects.get(id=course_id)
                queryset = course.search_reviews(query)
            except Course.DoesNotExist:
                return Response(
                    {"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND
                )

        # Apply author filter
        if request.query_params.get("author") == "me":
            queryset = queryset.filter(user=request.user)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        """Get list of reviews."""
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Create a new review for a course."""
        course_id = self.kwargs.get("course_id")
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response(
                {"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if user can write review
        if not Review.objects.user_can_write_review(request.user.id, course.id):
            logger.warning(
                f"User {request.user.id} cannot write review for course {course.id}"
            )
            return Response(
                {"detail": "User cannot write review"}, status=status.HTTP_403_FORBIDDEN
            )

        # Validate and save review using ReviewSerializer
        serializer = ReviewSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Review serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        review = serializer.save(course=course, user=request.user)

        # Return the created review
        serializer = self.get_serializer(review)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserReviewsAPI(
    generics.GenericAPIView,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    """API endpoint for user review operations - LIST, GET, PUT, DELETE."""

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "review_id"

    def get_queryset(self):
        """Only reviews belonging to the authenticated user."""
        return Review.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        """Handle both list (no id) and retrieve (with id) operations."""
        if "review_id" in kwargs:
            return self.retrieve(request, *args, **kwargs)
        else:
            return self.list(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """Update a specific review."""
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """Delete a specific review."""
        return self.destroy(request, *args, **kwargs)


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
            f"Missing required fields: value, forLayup in course vote API for course {course_id}"
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

    URL: /api/reviews/{review_id}/vote/
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
            logger.warning("Review %d not found for voting", review_id)
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
