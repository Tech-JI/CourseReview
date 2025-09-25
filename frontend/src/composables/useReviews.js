import { ref } from "vue";
import { getCookie } from "../utils/cookies";

export function useReviews() {
  const loading = ref(false);
  const error = ref(null);

  const fetchUserReview = async (courseId) => {
    if (!courseId) return null;
    try {
      const response = await fetch(`/api/course/${courseId}/my-review/`);
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data[0] : data;
      } else if (response.status === 404) {
        return null;
      } else {
        console.error(
          "useReviews: Error fetching user review",
          response.status,
        );
        return null;
      }
    } catch (e) {
      console.error("useReviews: Error fetching user review", e);
      return null;
    }
  };

  const submitReview = async (courseId, newReview) => {
    try {
      const response = await fetch(`/api/course/${courseId}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify(newReview),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to submit review");
      }
      return await response.json();
    } catch (e) {
      console.error("useReviews: submitReview error", e);
      throw e;
    }
  };

  const deleteReview = async (courseId) => {
    try {
      const response = await fetch(`/api/course/${courseId}/review/`, {
        method: "DELETE",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to delete review");
      }
      return await response.json();
    } catch (e) {
      console.error("useReviews: deleteReview error", e);
      throw e;
    }
  };

  const vote = async (courseId, value, forLayup) => {
    try {
      const response = await fetch(`/api/course/${courseId}/vote/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ value, forLayup }),
      });
      if (!response.ok) throw new Error("Vote failed");
      return await response.json();
    } catch (e) {
      console.error("useReviews: vote error", e);
      throw e;
    }
  };

  const voteOnReview = async (reviewId, isKudos) => {
    try {
      const response = await fetch(`/api/review/${reviewId}/vote/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ is_kudos: isKudos }),
      });
      if (!response.ok) throw new Error("Vote on review failed");
      return await response.json();
    } catch (e) {
      console.error("useReviews: voteOnReview error", e);
      throw e;
    }
  };

  return {
    loading,
    error,
    fetchUserReview,
    submitReview,
    deleteReview,
    vote,
    voteOnReview,
  };
}

export default { useReviews };
