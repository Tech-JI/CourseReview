import hashlib
import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, mixins, pagination, status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.web.models import (
    Course,
    CourseMedian,
    Instructor,
    Review,
    ReviewVote,
    Syllabus,
    SyllabusFile,
    Vote,
)
from apps.web.serializers import (
    CourseSearchSerializer,
    CourseSerializer,
    CourseVoteSerializer,
    ReviewSerializer,
    ReviewVoteSerializer,
    SyllabusAdminUpdateSerializer,
    SyllabusCreateSerializer,
    SyllabusSerializer,
)
from apps.web.tasks import process_syllabus
from lib.departments import get_department_name
from lib.grades import numeric_value_for_grade
from lib.terms import numeric_value_of_term

logger = logging.getLogger(__name__)


class CoursesPagination(pagination.PageNumberPagination):
    page_size = settings.WEB["COURSE"]["PAGE_SIZE"]


@ensure_csrf_cookie
@api_view(["GET"])
def user_status(request):
    """
    Get user authentication status.
    Input:
        - None
    Output:
        - Authenticated user: {"isAuthenticated": true, "username": "string",
          "is_staff": bool}
        - Anonymous user: {"isAuthenticated": false}
    """
    if request.user.is_authenticated:
        logger.info("User is authenticated")
        return Response(
            {
                "isAuthenticated": True,
                "username": request.user.username,
                "is_staff": request.user.is_staff,
            }
        )
    else:
        logger.info("User is not authenticated")
        return Response({"isAuthenticated": False})


@api_view(["GET"])
@permission_classes([AllowAny])
def landing_api(request):
    """
    Get landing page statistics.
    Input:
        - None
    Output:
        {"review_count": int}
    """
    return Response(
        {
            "review_count": Review.objects.count(),
        }
    )


class CoursesListAPI(generics.GenericAPIView, mixins.ListModelMixin):
    """
    List courses with filtering, sorting, and pagination.
    GET
    Input:
        - Query parameters:
            - department (string): Filter by department code (case-insensitive)
            - code (string): Filter by course code (partial match)
            - min_quality (integer): Filter by minimum quality score (authenticated only)
            - min_difficulty (integer): Filter by minimum difficulty score (authenticated only)
            - sort_by (string): Sort field ("course_code", "review_count"),("quality_score", "difficulty_score")(authenticated only)
            - sort_order (string): "asc" or "desc" (default: "asc")
            - page (integer): Page number for pagination

    Output:
        {
            "count": integer,
            "next": "string|null",
            "previous": "string|null",
            "results": [CourseSearchSerializer objects]
        }
    """

    serializer_class = CourseSearchSerializer
    permission_classes = [AllowAny]
    pagination_class = CoursesPagination

    def get_queryset(self):
        queryset = Course.objects.with_scores().prefetch_related("distribs")
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
                except ValueError, TypeError:
                    pass
        return queryset

    def _sort(self, queryset):
        """Helper function to sort courses based on request parameters."""
        sort_by = self.request.query_params.get("sort_by", "course_code")
        sort_order = self.request.query_params.get("sort_order", "asc")
        sort_prefix = "-" if sort_order.lower() == "desc" else ""

        allowed_sort_fields = ["course_code", "review_count"]
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
    """
    Retrieve details for a specific course.
    GET
    Input:
        - URL parameter: course_id (integer, required)

    Output:
        - CourseSerializer object
            - Authenticated: Full details
            - Non-authenticated: without scores, votes, and vote counts
    """

    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    lookup_field = "id"
    lookup_url_kwarg = "course_id"

    def get_queryset(self):
        queryset = Course.objects.with_scores_vote_counts()

        # Prefetch reviews with votes if authenticated
        request = self.request
        if request and request.user.is_authenticated:
            queryset = queryset.prefetch_related(
                Prefetch(
                    "review_set",
                    queryset=Review.objects.with_votes(vote_user=request.user),
                )
            )

        return queryset

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class CoursesReviewsAPI(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.CreateModelMixin
):
    """
    List and create reviews for a specific course.

    GET - List reviews:(Unused API)
    Input:
        - Authentication: Required
        - URL parameter: course_id (integer, required)
        - Query parameters:
            - q (string, optional): Search query for review content
            - author (string, optional): "me" to filter user's own reviews

    Output:
        - Success (200): [ReviewSerializer objects]

    POST - Create review:
    Input:
        - POST request
        - Authentication: Required
        - URL parameter: course_id (integer, required)
        - Body: "term","professor","comments"(required and only required)
    Output:
        Success (201): ReviewSerializer object
        Error (400): Validation errors
        Error (403): {"detail": "User cannot write review"}
        Error (404): {"detail": "Course not found"}
    """

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")
        try:
            course = Course.objects.get(id=course_id)
            return Review.objects.with_votes(vote_user=self.request.user, course=course)
        except Course.DoesNotExist:
            logger.warning("Course with id %d does not exist", course_id)
            return Review.objects.none()

    def list(self, request, *args, **kwargs):
        """List reviews with optional filtering."""
        queryset = self.get_queryset()

        # Apply author filter
        if request.query_params.get("author") == "me":
            queryset = queryset.filter(user=request.user)

        # Handle search query
        query = request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.order_by("-term").filter(
                Q(comments__icontains=query) | Q(professor__icontains=query)
            )

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
                "User %d cannot write review for course %d", request.user.id, course.id
            )
            return Response(
                {"detail": "User cannot write review"}, status=status.HTTP_403_FORBIDDEN
            )

        # Validate and save review using ReviewSerializer
        serializer = ReviewSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Review serializer errors: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(course=course, user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserReviewsAPI(
    generics.GenericAPIView,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    """
    Manage user's own reviews (CRUD operations).

    GET (List) - List user's reviews:(Unused API)
    Input:
        - Authentication: Required
        - URL parameter: None

    Output:
        Success (200): [ReviewSerializer objects]

    GET (Retrieve) - Get specific review:
    Input:
        - Authentication: Required
        - URL parameter: review_id (integer, required)

    Output:
        Success (200): ReviewSerializer object
        Error (404): {"detail": "Not found."}

    PUT - Update review:(Unused API)
    Input:
        - Authentication: Required
        - URL parameter: review_id (integer, required)
        - Body: "term","professor","comments"(required and only required)

    Output:
        Success (200): Updated ReviewSerializer object
        Error (400): Validation errors
        Error (404): {"detail": "Not found."}

    DELETE - Delete review:
    Input:
        - Authentication: Required
        - URL parameter: review_id (integer, required)

    Output:
        Success (204): No content
        Error (404): {"detail": "Not found."}
    """

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "review_id"

    def get_queryset(self):
        """Only reviews belonging to the authenticated user with vote annotations."""
        return Review.objects.with_votes(
            vote_user=self.request.user, user=self.request.user
        )

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
    """
    Get list of all departments with course counts.

    Input:
        - None

    Output:
        Success (200):
        [
            {
                "code": "string",
                "name": "string",
                "count": int
            }, ...
        ]
    """
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
@permission_classes([AllowAny])
def medians(request, course_id):
    """
    Unused API.
    """
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
@permission_classes([AllowAny])
def course_professors(request, course_id):
    """
    Unused API.
    """
    return Response(
        {
            "professors": sorted(
                set(
                    Review.objects.raw_queryset(course=course_id)
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
@permission_classes([AllowAny])
def course_instructors(request, course_id):
    """
    List instructors for a course (term-agnostic), as {id, name} objects.
    """
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        logger.warning("Course with id %d not found for instructors API", course_id)
        return Response({"error": "Course not found"}, status=404)
    instructors = (
        Instructor.objects.filter(courseoffering__course=course)
        .distinct()
        .order_by("name")
    )
    return Response(
        {"instructors": [{"id": i.id, "name": i.name} for i in instructors]}, status=200
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def course_vote_api(request, course_id):
    """
    Vote on course quality or difficulty.

    Input:
        - POST request
        - Authentication: Required
        - URL parameter: course_id (integer, required)
        - Body (JSON):
            {
                "value": integer (vote score between 1-5),
                "forLayup": boolean (true for difficulty, false for quality)
            }

    Output:
        Success (200):
        {
            "new_score": float,
            "was_unvote": boolean,
            "new_vote_count": integer
        }
        Error (400):
        {
            "detail": "Validation error with input fields"
        }
    """
    serializer = CourseVoteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    value = serializer.validated_data["value"]
    forLayup = serializer.validated_data["forLayup"]

    category = Vote.CATEGORIES.DIFFICULTY if forLayup else Vote.CATEGORIES.QUALITY
    new_score, is_unvote, new_vote_count = Vote.objects.vote(
        value, course_id, category, request.user
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
    Vote on reviews (kudos/dislike).

    Input:
        - POST request
        - Authentication: Required
        - URL parameter: review_id (integer, required)
        - Body (JSON):
            {
                "is_kudos": boolean (true for kudos, false for dislike)
            }
    Output:
        Success (200):
        {
            "kudos_count": integer,
            "dislike_count": integer,
            "user_vote": boolean|null (true/false/null)
        }
        Error (400):
        {
            "detail": "Validation error with input fields"
        }
    """
    serializer = ReviewVoteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    is_kudos = serializer.validated_data["is_kudos"]

    kudos_count, dislike_count, user_vote = ReviewVote.objects.vote(
        review_id=review_id, user=request.user, is_kudos=is_kudos
    )

    if kudos_count is None or dislike_count is None:
        # Review doesn't exist
        logger.warning("Review %s not found for voting", str(review_id))
        return Response({"detail": "Review not found"}, status=404)

    return Response(
        {
            "kudos_count": kudos_count,
            "dislike_count": dislike_count,
            "user_vote": user_vote,
        }
    )


class CourseSyllabiAPI(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.CreateModelMixin
):
    """
    List or upload syllabi for a course.

    GET: public, lists SyllabusSerializer rows (newest first).
    POST: authenticated, multipart {file, instructor}; dedupes by sha256.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        return Syllabus.objects.filter(course_id=self.kwargs["course_id"])

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SyllabusCreateSerializer
        return SyllabusSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        course_id = self.kwargs.get("course_id")
        if not Course.objects.filter(pk=course_id).exists():
            return Response(
                {"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )
        queryset = self.get_queryset().select_related(
            "instructor", "file", "uploaded_by"
        )
        serializer = SyllabusSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        course_id = self.kwargs.get("course_id")
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response(
                {"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = SyllabusCreateSerializer(
            data=request.data, context={"course": course}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        upload = serializer.validated_data["file"]
        instructor_id = serializer.validated_data["instructor"]
        content = upload.read()
        digest = hashlib.sha256(content).hexdigest()

        # Reuse an existing SyllabusFile (same bytes already on disk).
        file_obj = SyllabusFile.objects.filter(sha256=digest).first()
        if file_obj is None:
            name = upload.name.lower()
            ext = ".pdf" if name.endswith(".pdf") else ".docx"
            file_obj = SyllabusFile(
                sha256=digest,
                content_type=upload.content_type or "",
                original_filename=upload.name,
                size=len(content),
            )
            try:
                file_obj.file.save(f"{digest}{ext}", ContentFile(content), save=True)
            except IntegrityError:
                # Lost a concurrent identical upload race; reuse the winner.
                file_obj = SyllabusFile.objects.get(sha256=digest)

        # Idempotent re-upload of the same file for the same course+instructor.
        existing = Syllabus.objects.filter(
            course=course, instructor_id=instructor_id, file=file_obj
        ).first()
        if existing:
            return Response(
                SyllabusSerializer(existing).data, status=status.HTTP_200_OK
            )

        syllabus = Syllabus.objects.create(
            course=course,
            instructor_id=instructor_id,
            file=file_obj,
            uploaded_by=request.user,
            status=Syllabus.Status.PENDING,
        )
        try:
            process_syllabus.delay(syllabus.id)
        except Exception:  # noqa: BLE001 - broker down; task stays pending
            logger.exception("Failed to enqueue syllabus analysis %d", syllabus.id)
        # Eager execution (tests) may already have analyzed this row.
        syllabus.refresh_from_db()
        return Response(
            SyllabusSerializer(syllabus).data, status=status.HTTP_201_CREATED
        )


class SyllabusDetailAPI(
    generics.GenericAPIView, mixins.RetrieveModelMixin, mixins.UpdateModelMixin
):
    """
    Syllabus detail. GET public; PATCH staff-only (summary/verdict/primary).
    """

    serializer_class = SyllabusSerializer
    queryset = Syllabus.objects.select_related("instructor", "file", "uploaded_by")
    lookup_field = "pk"
    lookup_url_kwarg = "syllabus_id"

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return SyllabusAdminUpdateSerializer
        return SyllabusSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [IsAdminUser()]
        return [AllowAny()]

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        syllabus = self.get_object()
        serializer = SyllabusAdminUpdateSerializer(
            syllabus, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        syllabus = serializer.save()
        if serializer.validated_data.get("is_primary"):
            Syllabus.objects.filter(
                course=syllabus.course,
                instructor=syllabus.instructor,
            ).exclude(pk=syllabus.pk).update(is_primary=False)
        return Response(SyllabusSerializer(syllabus).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def syllabus_download(request, syllabus_id):
    """Stream the original uploaded file; logged-in users only."""
    try:
        syllabus = Syllabus.objects.select_related("file").get(pk=syllabus_id)
    except Syllabus.DoesNotExist:
        logger.warning("Syllabus %s not found for download", syllabus_id)
        return Response({"detail": "Syllabus not found"}, status=404)
    file_obj = syllabus.file
    response = FileResponse(
        file_obj.file.open("rb"),
        as_attachment=True,
        filename=file_obj.original_filename,
        content_type=file_obj.content_type or "application/octet-stream",
    )
    return response
