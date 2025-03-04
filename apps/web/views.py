import datetime
import uuid

import dateutil.parser
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_safe
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.recommendations.models import Recommendation
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
from apps.web.serializers import CourseSerializer
from lib import constants
from lib.departments import get_department_name
from lib.grades import numeric_value_for_grade
from lib.terms import numeric_value_of_term

# from google.cloud import pubsub_v1

# pub_sub_publisher = pubsub_v1.PublisherClient()
# topic_paths = {
#     'course-views': pub_sub_publisher.topic_path(os.environ['GCLOUD_PROJECT_ID'], 'course-views')
# }

LIMITS = {
    "courses": 20,
    "reviews": 5,
    "unauthenticated_review_search": 3,
}


# def get_user(request):
#     if request.user.is_authenticated:
#         return Response(
#             {"user": {"id": request.user.id, "username": request.user.username}}
#         )
#     else:
#         return Response({"user": None})


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


@require_safe
def landing(request):
    return render(
        request,
        "landing.html",
        {
            "page_javascript": "LayupList.Web.Landing()",
            "review_count": Review.objects.count(),
        },
    )


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


def auth_login(request):
    if request.method == "POST":
        username = request.POST.get("email").lower().split("@")[0]
        password = request.POST.get("password")
        next_url = request.GET.get("next", "/layups")

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                if "user_id" in request.session:
                    student = Student.objects.get(user=user)
                    student.unauth_session_ids.append(request.session["user_id"])
                    student.save()
                request.session["user_id"] = user.username

                return redirect(next_url)
            else:
                return render(
                    request,
                    "login.html",
                    {
                        "error": (
                            "Please activate your account via the activation link "
                            "first."
                        )
                    },
                )
        else:
            return render(request, "login.html", {"error": "Invalid login."})
    elif request.method == "GET":
        return render(request, "login.html")
    else:
        return render(request, "login.html", {"error": "Please authenticate."})


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


@require_safe
def current_term(request, sort):
    if sort == "best":
        course_type, primary_sort, secondary_sort = (
            "Best Classes",
            "-quality_score",
            "-difficulty_score",
        )
        vote_category = Vote.CATEGORIES.QUALITY
    else:
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse("signup") + "?restriction=see layups")

        course_type, primary_sort, secondary_sort = (
            "Layups",
            "-difficulty_score",
            "-quality_score",
        )
        vote_category = Vote.CATEGORIES.DIFFICULTY

    dist = request.GET.get("dist")
    dist = dist.upper() if dist else dist
    term_courses = (
        Course.objects.for_term(constants.CURRENT_TERM, dist)
        .prefetch_related("distribs", "review_set", "courseoffering_set")
        .order_by(primary_sort, secondary_sort)
    )

    paginator = Paginator(term_courses, LIMITS["courses"])
    try:
        courses = paginator.page(request.GET.get("page"))
    except PageNotAnInteger:
        courses = paginator.page(1)
    except EmptyPage:
        courses = paginator.page(paginator.num_pages)

    if courses.number > 1 and not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("signup") + "?restriction=see more")

    for_layups_js_boolean = str(sort != "best").lower()

    courses_and_votes = Vote.objects.authenticated_group_courses_with_votes(
        courses.object_list, vote_category, request.user
    )

    return render(
        request,
        "current_term.html",
        {
            "term": constants.CURRENT_TERM,
            "sort": sort,
            "course_type": course_type,
            "courses": courses,
            "courses_and_votes": courses_and_votes,
            "distribs": DistributiveRequirement.objects.all(),
            "page_javascript": "LayupList.Web.CurrentTerm({})".format(
                for_layups_js_boolean
            ),
        },
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

    if len(query) < 2:
        return Response({"query": query, "department": None, "courses": []})

    courses = Course.objects.search(query).prefetch_related(
        "review_set", "courseoffering_set", "distribs"
    )

    if len(query) not in Course.objects.DEPARTMENT_LENGTHS:
        courses = sorted(courses, key=lambda c: c.review_set.count(), reverse=True)

    serializer = CourseSerializer(courses, many=True, context={"request": request})

    return Response(
        {
            "query": query,
            "department": get_department_name(query),
            "term": constants.CURRENT_TERM,
            "courses": serializer.data,
        }
    )


@require_safe
def course_review_search(request, course_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("signup") + "?restriction=see reviews")

    query = request.GET.get("q", "").strip()
    course = Course.objects.get(id=course_id)
    reviews = course.search_reviews(query)
    review_count = reviews.count()

    if not request.user.is_authenticated:
        reviews = reviews[: LIMITS["unauthenticated_review_search"]]

    return render(
        request,
        "course_review_search.html",
        {
            "query": query,
            "course": course,
            "reviews_full_count": review_count,
            "remaining": review_count - LIMITS["unauthenticated_review_search"],
            "reviews": reviews,
            "page_javascript": "LayupList.Web.CourseReviewSearch()",
        },
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
