import datetime
import re
import uuid

import dateutil.parser
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Q
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_safe
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

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
@permission_classes([AllowAny])
def auth_login_api(request):
    email = request.data.get("email", "").lower()
    password = request.data.get("password", "")
    next_url = request.data.get("next", "/layups")

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=400)

    username = email.split("@")[0]
    user = authenticate(username=username, password=password)

    if user is not None:
        if user.is_active:
            login(request, user)
            if "user_id" in request.session:
                student = Student.objects.get(user=user)
                student.unauth_session_ids.append(request.session["user_id"])
                student.save()
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


@login_required
def auth_logout(request):
    logout(request)
    request.session["userID"] = uuid.uuid4().hex
    return render(request, "logout.html")


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
    dist = request.GET.get("dist", "").upper()
    # e.g., quality_desc, difficulty_asc, code
    requested_sort = request.GET.get("sort", "code")
    page = request.GET.get("page", 1)

    base_query = Course.objects.all()
    sort_applied = requested_sort  # Keep track of what sort is actually applied
    sort_overridden = False

    # Apply text search filter if query is provided
    if len(query) >= 2:
        department_match = re.match(r"([a-zA-Z]+)\s*(\d*)", query)
        if department_match:
            dept_code = department_match.group(1).upper()
            num_str = department_match.group(2)
            q_filter = Q(department__iexact=dept_code)
            if num_str:
                try:
                    num = int(num_str)
                    q_filter &= Q(number=num)
                except ValueError:
                    q_filter = (
                        Q(course_title__icontains=query)
                        | Q(description__icontains=query)
                        | Q(course_code__icontains=query)
                    )
            else:
                q_filter |= Q(course_title__icontains=query) | Q(
                    description__icontains=query
                )
        else:
            q_filter = (
                Q(course_title__icontains=query)
                | Q(description__icontains=query)
                | Q(course_code__icontains=query)
            )
        base_query = base_query.filter(q_filter)
    elif query:
        if not dist:
            base_query = base_query.none()

    # Apply distributive requirement filter
    if dist:
        base_query = base_query.filter(distribs__name=dist)

    # Apply sorting with authentication check
    sort_field = requested_sort.replace("_asc", "").replace("_desc", "")
    sort_direction = "-" if requested_sort.endswith("_desc") else ""

    if sort_field in ["quality", "difficulty"] and not request.user.is_authenticated:
        # Unauthenticated user requested score-based sort, override to 'code'
        sort_applied = "code"
        sort_overridden = True
        base_query = base_query.order_by("department", "number")
    elif sort_field == "quality":
        base_query = base_query.order_by(
            f"{sort_direction}quality_score",
            f"{sort_direction}difficulty_score",
            "course_code",
        )
        sort_applied = requested_sort
    elif sort_field == "difficulty":
        base_query = base_query.order_by(
            f"{sort_direction}difficulty_score",
            f"{sort_direction}quality_score",
            "course_code",
        )
        sort_applied = requested_sort
    else:
        sort_applied = "code"
        base_query = base_query.order_by(
            f"{sort_direction}department", f"{sort_direction}number"
        )

    # Prefetch related data
    courses_filtered = base_query.prefetch_related(
        "review_set",
        "distribs",
        "courseoffering_set",
        "courseoffering_set__instructors",
    )

    # Pagination
    paginator = Paginator(courses_filtered, LIMITS["courses"])
    try:
        courses_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        courses_page = paginator.page(1)

    if (
        sort_field == "difficulty"
        and courses_page.number > 1
        and not request.user.is_authenticated
    ):
        return Response(
            {"detail": "Authentication required to view more pages of layups"},
            status=403,
        )

    serializer = CourseSearchSerializer(
        courses_page.object_list, many=True, context={"request": request}
    )

    # Determine department name if query matches a department code
    department_name = None
    if (
        query
        and len(query) in Course.objects.DEPARTMENT_LENGTHS
        and courses_filtered.exists()
        and courses_filtered.filter(department__iexact=query).count()
        == courses_filtered.count()
    ):
        department_name = get_department_name(query.upper())

    response_data = {
        "query": query,
        "department": department_name,
        "term": constants.CURRENT_TERM,
        "courses": serializer.data,
        "current_page": courses_page.number,
        "total_pages": paginator.num_pages,
        "distribs": [
            {"name": d.name, "code": d.name}
            for d in DistributiveRequirement.objects.all().order_by("name")
        ],
        "selected_distrib": dist if dist else None,
        "selected_sort": sort_applied,
    }

    if sort_overridden:
        response_data["message"] = (
            "Sorting by score requires login. Defaulted to sorting by code."
        )

    return Response(response_data)


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
def vote(request, course_id):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    try:
        value = request.POST["value"]
        forLayup = request.POST["forLayup"] == "true"
    except KeyError:
        return HttpResponseBadRequest()

        category = Vote.CATEGORIES.DIFFICULTY if forLayup else Vote.CATEGORIES.QUALITY
        new_score, is_unvote = Vote.objects.vote(
            int(value), course_id, category, request.user
        )

        return JsonResponse({"new_score": new_score, "was_unvote": is_unvote})
