import datetime
import uuid

import dateutil.parser
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


from apps.web.models import (
    Course,
    CourseMedian,
    DistributiveRequirement,
    Instructor,
    Review,
    Student,
    Vote,
)
from apps.web.models.forms import ReviewForm, SignupForm
from apps.web.serializers import (
    CourseSearchSerializer,
    CourseSerializer,
    ReviewSerializer,
)
from lib import constants
from lib.departments import get_department_name
from lib.grades import numeric_value_for_grade
from lib.terms import numeric_value_of_term

LIMITS = {
    "courses": 20,
    "reviews": 5,
    "unauthenticated_review_search": 3,
}


@api_view(["GET"])
def user_status(request):
    if request.user.is_authenticated:
        return Response({"isAuthenticated": True, "username": request.user.username})
    else:
        return Response({"isAuthenticated": False})


def get_session_id(request):
    if "user_id" not in request.session:
        if not request.user.is_authenticated:
            request.session["user_id"] = uuid.uuid4().hex
        else:
            request.session["user_id"] = request.user.username
    return request.session["user_id"]


@api_view(["GET"])
@permission_classes([AllowAny])
def landing_api(request):
    """API endpoint for landing page data"""
    return Response(
        {
            "review_count": Review.objects.count(),
        }
    )


def get_prior_course_id(request, current_course_id):
    prior_course_id = None
    if (
        "prior_course_id" in request.session
        and "prior_course_timestamp" in request.session
    ):
        prior_course_timestamp = request.session["prior_course_timestamp"]
        if (
            dateutil.parser.parse(prior_course_timestamp)
            + datetime.timedelta(minutes=10)
            >= datetime.datetime.now()
        ):
            prior_course_id = request.session["prior_course_id"]
    request.session["prior_course_id"] = current_course_id
    request.session["prior_course_timestamp"] = datetime.datetime.now().isoformat()
    return prior_course_id


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save_and_send_confirmation(request)
            return render(request, "instructions.html")
        else:
            return render(request, "signup.html", {"form": form})

    else:
        return render(request, "signup.html", {"form": SignupForm()})


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def auth_login_api(request):
    email = request.data.get("email", "").lower()
    password = request.data.get("password", "")
    next_url = request.data.get("next", "/courses")

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=400)

    username = email.split("@")[0]
    user = authenticate(username=username, password=password)

    if user is not None:
        if user.is_active:
            login(request, user)
            if "user_id" in request.session:
                try:
                    student = Student.objects.get(user=user)
                    student.unauth_session_ids.append(request.session["user_id"])
                    student.save()
                except Student.DoesNotExist:
                    student = Student.objects.create(
                        user=user, unauth_session_ids=[request.session["user_id"]]
                    )
            request.session["user_id"] = user.username

            return Response(
                {"success": True, "next": next_url, "username": user.username}
            )
        else:
            return Response(
                {
                    "error": "Please activate your account via the activation link first."
                },
                status=403,
            )
    else:
        return Response({"error": "Invalid email or password"}, status=401)


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def auth_logout_api(request):
    """
    API endpoint for user logout.
    """
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            if "user_id" in request.session:
                if request.session["user_id"] in student.unauth_session_ids:
                    student.unauth_session_ids.remove(request.session["user_id"])
                    student.save()
        except Student.DoesNotExist:
            pass

        logout(request)
        request.session["userID"] = uuid.uuid4().hex
        return Response({"success": True, "message": "Logged out successfully"})
    else:
        return Response(
            {"success": False, "message": "User not authenticated"}, status=400
        )


@require_safe
def confirmation(request):
    link = request.GET.get("link")

    if link:
        try:
            student = Student.objects.get(confirmation_link=link)
        except Student.DoesNotExist:
            return render(
                request,
                "confirmation.html",
                {"error": "Confirmation code expired or does not exist."},
            )

        if student.user.is_active:
            return render(request, "confirmation.html", {"already_confirmed": True})

        student.user.is_active = True
        student.user.save()
        return render(request, "confirmation.html", {"already_confirmed": False})
    else:
        return render(
            request, "confirmation.html", {"error": "Please provide confirmation code."}
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def courses_api(request):
    """
    API endpoint for listing courses with filtering, sorting, and pagination.
    """
    queryset = Course.objects.all().prefetch_related("distribs", "review_set")
    queryset = queryset.annotate(num_reviews=Count("review"))

    # --- Filtering ---
    department = request.query_params.get("department")
    if department:
        queryset = queryset.filter(department__iexact=department)

    code = request.query_params.get("code")
    if code:
        queryset = queryset.filter(course_code__icontains=code)

    if request.user.is_authenticated:
        min_quality = request.query_params.get("min_quality")
        if min_quality:
            try:
                queryset = queryset.filter(quality_score__gte=int(min_quality))
            except (ValueError, TypeError):
                pass  # Ignore invalid values

        min_difficulty = request.query_params.get("min_difficulty")  # Layup score
        if min_difficulty:
            try:
                queryset = queryset.filter(difficulty_score__gte=int(min_difficulty))
            except (ValueError, TypeError):
                pass  # Ignore invalid values

    # --- Sorting ---
    sort_by = request.query_params.get("sort_by", "course_code")  # Default sort
    sort_order = request.query_params.get("sort_order", "asc")
    sort_prefix = "-" if sort_order.lower() == "desc" else ""

    allowed_sort_fields = ["course_code", "num_reviews"]
    if request.user.is_authenticated:
        allowed_sort_fields.extend(["quality_score", "difficulty_score"])

    if sort_by in allowed_sort_fields:
        sort_field = sort_by
    else:
        sort_field = "course_code"  # Fallback to default if invalid or not allowed

    queryset = queryset.order_by(f"{sort_prefix}{sort_field}")

    # --- Pagination ---
    paginator = Paginator(queryset, LIMITS["courses"])
    page_number = request.query_params.get("page", 1)
    try:
        page = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page = paginator.page(1)

    # --- Serialization ---
    serializer = CourseSearchSerializer(
        page.object_list, many=True, context={"request": request}
    )

    return Response(
        {
            "courses": serializer.data,
            "pagination": {
                "current_page": page.number,
                "total_pages": paginator.num_pages,
                "total_courses": paginator.count,
                "limit": LIMITS["courses"],
            },
            "query_params": request.query_params,  # Return applied params for context
        }
    )


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def course_detail_api(request, course_id):
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return Response(status=404)

    if request.method == "GET":
        serializer = CourseSerializer(course, context={"request": request})
        return Response(serializer.data)
    elif request.method == "POST":
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=403)

        if not Review.objects.user_can_write_review(request.user.id, course_id):
            return Response({"detail": "User cannot write review"}, status=403)

        form = ReviewForm(request.data)
        if form.is_valid():
            review = form.save(commit=False)
            review.course = course
            review.user = request.user
            review.save()
            serializer = CourseSerializer(
                course, context={"request": request}
            )  # re-serialize with new data
            return Response(serializer.data, status=201)
        return Response(form.errors, status=400)


@api_view(["DELETE"])
@permission_classes([AllowAny])
def delete_review_api(request, course_id):
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return Response({"detail": "Authentication required"}, status=403)
    course = Course.objects.get(id=course_id)
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
@permission_classes([AllowAny])
def course_search_api(request):
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return Response({"query": query, "department": None, "courses": []})

    courses = Course.objects.search(query).prefetch_related("review_set", "distribs")

    if len(query) not in Course.objects.DEPARTMENT_LENGTHS:
        courses = sorted(courses, key=lambda c: c.review_set.count(), reverse=True)

    serializer = CourseSearchSerializer(
        courses, many=True, context={"request": request}
    )

    return Response(
        {
            "query": query,
            "department": get_department_name(query),
            "term": constants.CURRENT_TERM,
            "courses": serializer.data,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def course_review_search_api(request, course_id):
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return Response({"detail": "Course not found"}, status=404)

    query = request.GET.get("q", "").strip()
    reviews = course.search_reviews(query)
    review_count = reviews.count()

    if not request.user.is_authenticated:
        reviews = reviews[: LIMITS["unauthenticated_review_search"]]

    serializer = ReviewSerializer(reviews, many=True)

    return Response(
        {
            "query": query,
            "course_id": course.id,
            "course_short_name": course.short_name(),
            "reviews_full_count": review_count,
            "remaining": (
                review_count - LIMITS["unauthenticated_review_search"]
                if review_count > LIMITS["unauthenticated_review_search"]
                else 0
            ),
            "reviews": serializer.data,
        }
    )


@require_safe
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

    return JsonResponse(
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
        }
    )


@require_safe
def course_professors(request, course_id):
    return JsonResponse(
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
        }
    )


@require_safe
def course_instructors(request, course_id):
    try:
        course = Course.objects.get(pk=course_id)
        instructors = course.get_instructors()
        return JsonResponse(
            {"instructors": [instructor.name for instructor in instructors]}
        )
    except Course.DoesNotExist:
        return JsonResponse({"error": "Course not found"}, status=404)


@require_POST
def course_vote_api(request, course_id):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    try:
        import json

        if request.content_type == "application/json":
            data = json.loads(request.body)
            value = data["value"]
            forLayup = data["forLayup"]
        else:
            value = request.POST["value"]
            forLayup = request.POST["forLayup"]
    except (KeyError, json.JSONDecodeError):
        return HttpResponseBadRequest()

    category = Vote.CATEGORIES.DIFFICULTY if forLayup else Vote.CATEGORIES.QUALITY
    new_score, is_unvote, new_vote_count = Vote.objects.vote(
        int(value), course_id, category, request.user
    )

    return JsonResponse(
        {
            "new_score": new_score,
            "was_unvote": is_unvote,
            "new_vote_count": new_vote_count,
        }
    )
