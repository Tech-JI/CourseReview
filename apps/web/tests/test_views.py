from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.web.tests import factories
from apps.web.models import Review


class LandingApiTests(APITestCase):
    def setUp(self):
        self.course = factories.CourseFactory()
        factories.ReviewFactory.create_batch(3, course=self.course)

    def test_get_review_count(self):
        url = reverse("landing_api")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["review_count"], 3)


class UserStatusTests(APITestCase):
    """Test user authentication status interface"""

    def setUp(self):
        # Prepare a test user
        self.user = factories.UserFactory(username="test_student")
        # Matches name="user_status" in urls.py
        self.url = reverse("user_status")

    def test_user_is_not_authenticated(self):
        """Test access for unauthenticated users"""
        # Send GET request
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Per views.py: Anonymous users should return {"isAuthenticated": False}
        self.assertEqual(response.data["isAuthenticated"], False)
        # Ensure 'username' field is not present in the response for anonymous users
        self.assertNotIn("username", response.data)

    def test_user_is_authenticated(self):
        """Test access for authenticated users"""
        # --- Core step: Mock login ---
        # This forces the client to be authenticated as self.user
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Per views.py: Authenticated users should return {"isAuthenticated": True, "username": "..."}
        self.assertEqual(response.data["isAuthenticated"], True)
        self.assertEqual(response.data["username"], "test_student")


class CourseListApiTests(APITestCase):
    """Test course list interface (supports pagination, filtering, sorting)"""

    def setUp(self):
        # 1. Prepare courses with different departments and codes
        # Ensure the corrected field name 'course_title' is used
        self.c1 = factories.CourseFactory(
            department="COSC", course_code="COSC010", course_title="Intro to CS"
        )
        self.c2 = factories.CourseFactory(
            department="COSC", course_code="COSC101", course_title="Data Structure"
        )
        self.c3 = factories.CourseFactory(
            department="MATH", course_code="MATH001", course_title="Calculus"
        )

        self.url = reverse("courses_api")

    def test_get_course_list_pagination(self):
        """Test basic pagination response structure"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Key point: DRF paginated response returns a dict containing 'results' and 'count'
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        # Check if total count is correct
        self.assertEqual(response.data["count"], 3)

    def test_filter_by_department(self):
        """Test filtering by department (?department=COSC)"""
        # Send request with query parameters
        response = self.client.get(self.url, {"department": "COSC"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return exactly two COSC courses
        self.assertEqual(response.data["count"], 2)
        # Verify the returned courses belong to COSC
        for course in response.data["results"]:
            self.assertTrue(course["course_code"].startswith("COSC"))

    def test_filter_by_course_code(self):
        """Test fuzzy search by course code (?code=101)"""
        response = self.client.get(self.url, {"code": "101"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only COSC101 contains '101'
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["course_code"], "COSC101")

    def test_sort_by_course_code_desc(self):
        """Test sorting functionality (?sort_by=course_code&sort_order=desc)"""
        params = {"sort_by": "course_code", "sort_order": "desc"}
        response = self.client.get(self.url, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check sorting: Descending order should start with MATH001 (as M > C)
        # Or among same initials: COSC101 > COSC010
        self.assertEqual(response.data["results"][0]["course_code"], "MATH001")


class CourseReviewApiTests(APITestCase):
    """Test course review interface (GET and POST)"""

    def setUp(self):
        self.user = factories.UserFactory()
        self.course = factories.CourseFactory()
        # Matches name="course_review_api" in urls.py
        self.url = reverse("course_review_api", kwargs={"course_id": self.course.id})

    def test_get_reviews(self):
        """Test retrieving review list for a specific course"""
        # Mock login (this API requires IsAuthenticated)
        self.client.force_authenticate(user=self.user)
        # Create 2 reviews for this course
        factories.ReviewFactory.create_batch(2, course=self.course)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # This API returns a list directly, not a paginated object
        self.assertEqual(len(response.data), 2)

    def test_post_review_success(self):
        """Test successful review post by authenticated user"""
        self.client.force_authenticate(user=self.user)

        data = {
            "term": "23F",  # Ensure this matches the database max_length constraint
            "professor": "Dr. Smith",
            "comments": "This course is amazing and very useful.",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify database state
        self.assertEqual(Review.objects.filter(course=self.course).count(), 1)
        self.assertEqual(Review.objects.first().professor, "Dr. Smith")

    def test_post_review_anonymous(self):
        """Test unauthenticated users cannot post reviews"""
        data = {"term": "23F", "professor": "X", "comments": "Y"}
        response = self.client.post(self.url, data, format="json")

        # Expecting 401 Unauthorized or 403 Forbidden
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_post_review_duplicate_forbidden(self):
        """
        Test users cannot post duplicate reviews for the same course
        (Verify 'user_can_write_review' logic in views.py)
        """
        self.client.force_authenticate(user=self.user)
        # Create an existing review for this user and course
        factories.ReviewFactory(course=self.course, user=self.user)

        data = {"term": "23F", "professor": "X", "comments": "New comment"}
        response = self.client.post(self.url, data, format="json")

        # Expecting 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "User cannot write review")


class CourseVoteApiTests(APITestCase):
    """Test course rating interface (quality and difficulty voting)"""

    def setUp(self):
        self.user = factories.UserFactory()
        self.course = factories.CourseFactory()
        # Matches name="course_vote_api" in urls.py
        self.url = reverse("course_vote_api", kwargs={"course_id": self.course.id})

    def test_vote_quality_success(self):
        """Test voting on course quality"""
        self.client.force_authenticate(user=self.user)
        data = {"value": 5, "forLayup": False}  # forLayup=False represents quality
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify new score and count are returned
        self.assertIn("new_score", response.data)
        self.assertEqual(response.data["new_vote_count"], 1)

    def test_vote_invalid_value(self):
        """Test invalid vote score (e.g., 10)"""
        self.client.force_authenticate(user=self.user)
        data = {"value": 10, "forLayup": False}
        response = self.client.post(self.url, data, format="json")
        # Should return 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ReviewVoteApiTests(APITestCase):
    """Test review kudos/dislike interface"""

    def setUp(self):
        self.user = factories.UserFactory()
        self.review = (
            factories.ReviewFactory()
        )  # Automatically creates a course and an author
        self.url = reverse("review_vote_api", kwargs={"review_id": self.review.id})

    def test_review_kudos(self):
        """Test kudos for a review"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"is_kudos": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["kudos_count"], 1)
        self.assertTrue(response.data["user_vote"])


class UserReviewsApiTests(APITestCase):
    """Test personal review management interface (CRUD)"""

    def setUp(self):
        self.user = factories.UserFactory()
        # 1. Define self.course for subsequent use
        self.course = factories.CourseFactory()

        # 2. Create my own review associated with self.course
        self.my_review = factories.ReviewFactory(
            user=self.user, course=self.course, comments="My own review"
        )

        # 3. Create a review belonging to another user
        self.other_review = factories.ReviewFactory(comments="Other's review")

        # 4. Define URLs
        self.list_url = reverse("user_reviews_api")
        self.url = reverse("user_review_api", kwargs={"review_id": self.my_review.id})

    def test_get_my_reviews_list(self):
        """Test retrieving the list of 'my reviews'"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see my own review
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["comments"], "My own review")

    def test_delete_my_review(self):
        """Test deleting my own review"""
        self.client.force_authenticate(user=self.user)
        url = reverse("user_review_api", kwargs={"review_id": self.my_review.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Review.objects.filter(id=self.my_review.id).count(), 0)

    def test_delete_others_review_forbidden(self):
        """Test forbidden from deleting others' reviews"""
        self.client.force_authenticate(user=self.user)
        # Attempt to delete a review ID belonging to another user
        url = reverse("user_review_api", kwargs={"review_id": self.other_review.id})
        response = self.client.delete(url)

        # Should return 404 as the queryset filters out reviews not owned by the user
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_my_review(self):
        """Test updating my own review"""
        self.client.force_authenticate(user=self.user)

        # Prepare data for update
        updated_data = {
            "course": self.course.id,  # self.course is defined in setUp
            "term": "23F",
            "professor": "New Professor",
            "comments": "This content has been updated.",
        }

        # Send PUT request
        response = self.client.put(self.url, updated_data, format="json")

        # --- If 400 error occurs, this prints debug validation details ---
        if response.status_code == 400:
            print(f"\n[DEBUG] Validation failed: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh database record and verify if content has changed
        self.my_review.refresh_from_db()
        self.assertEqual(self.my_review.comments, "This content has been updated.")


class CourseDetailApiTests(APITestCase):
    """Test course detail interface (auth vs unauth permissions)"""

    def setUp(self):
        self.user = factories.UserFactory()
        self.course = factories.CourseFactory(course_title="Detail Science")
        self.url = reverse("course_detail_api", kwargs={"course_id": self.course.id})

    def test_get_course_detail_anonymous(self):
        """Test unauthenticated users viewing details"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["course_title"], "Detail Science")
        # Anonymous users should not see sensitive fields (depending on Serializer definition)

    def test_get_course_detail_authenticated(self):
        """Test authenticated users viewing details (triggers prefetch logic)"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.course.id)
