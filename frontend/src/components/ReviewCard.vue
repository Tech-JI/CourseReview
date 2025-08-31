<template>
  <div class="bg-white overflow-hidden shadow rounded-2xl ring-1 ring-indigo-100">
    <div class="px-4 py-5 sm:p-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center">
          <div
            v-if="review.term"
            class="text-sm font-medium text-indigo-800"
          >
            {{ review.term }}
            <span v-if="review.professor" class="text-indigo-600">
              with {{ review.professor }}</span
            >
          </div>
        </div>
        <div v-if="review.created_at" class="text-xs text-indigo-500">
          {{ new Date(review.created_at).toLocaleDateString() }}
        </div>
      </div>

      <!-- Use MdPreview for displaying review comments -->
      <div class="mt-4">
        <MdPreview
          :model-value="truncatedContent"
          :sanitize="sanitize"
          previewTheme="github"
          class="text-sm text-indigo-700 markdown-content"
        />

        <!-- Enhanced Expand/Collapse button -->
        <div v-if="needsTruncation" class="mt-3 flex justify-center">
          <button
            @click="expanded = !expanded"
            class="inline-flex items-center gap-x-1.5 rounded-md bg-indigo-50 px-2.5 py-1.5 text-xs font-semibold text-indigo-600 shadow-xs hover:bg-indigo-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 transition-all"
          >
            {{ expanded ? "Show Less" : "Read More" }}
            <svg
              :class="[
                'h-3 w-3 transition-transform duration-200',
                expanded && 'rotate-180',
              ]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
        </div>
      </div>

      <!-- Review Voting Section -->
      <div v-if="isAuthenticated" class="mt-6 flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <!-- Kudos Button -->
          <button
            @click="handleVote(review.id, true)"
            :class="[
              'inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-full transition-colors',
              review.user_vote === true
                ? 'bg-green-100 text-green-800 hover:bg-green-200'
                : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100',
            ]"
            :title="
              review.user_vote === true
                ? 'Remove kudos'
                : 'Give kudos'
            "
          >
            <HandThumbUpIcon
              :class="[
                'mr-1.5 h-4 w-4',
                review.user_vote === true
                  ? 'text-green-600'
                  : 'text-indigo-400',
              ]"
            />
            {{ review.kudos_count || 0 }}
          </button>

          <!-- Dislike Button -->
          <button
            @click="handleVote(review.id, false)"
            :class="[
              'inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-full transition-colors',
              review.user_vote === false
                ? 'bg-red-100 text-red-800 hover:bg-red-200'
                : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100',
            ]"
            :title="
              review.user_vote === false
                ? 'Remove dislike'
                : 'Dislike'
            "
          >
            <HandThumbDownIcon
              :class="[
                'mr-1.5 h-4 w-4',
                review.user_vote === false
                  ? 'text-red-600'
                  : 'text-indigo-400',
              ]"
            />
            {{ review.dislike_count || 0 }}
          </button>
        </div>
      </div>
      <!-- Vote counts display only (for non-authenticated users) -->
      <div v-else class="mt-6 flex items-center space-x-4">
        <!-- Kudos Count -->
        <div
          v-if="review.kudos_count > 0"
          class="inline-flex items-center text-sm text-green-600"
        >
          <HandThumbUpIcon class="mr-1.5 h-4 w-4" />
          {{ review.kudos_count }}
        </div>

        <!-- Dislikes Count -->
        <div
          v-if="review.dislike_count > 0"
          class="inline-flex items-center text-sm text-red-600"
        >
          <HandThumbDownIcon class="mr-1.5 h-4 w-4" />
          {{ review.dislike_count }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { MdPreview } from "md-editor-v3";
import {
  HandThumbUpIcon,
  HandThumbDownIcon,
} from "@heroicons/vue/24/outline";
import "md-editor-v3/lib/style.css";

const props = defineProps({
  review: {
    type: Object,
    required: true,
  },
  isAuthenticated: {
    type: Boolean,
    default: false,
  },
  sanitize: {
    type: Function,
    required: true,
  },
  maxLines: {
    type: Number,
    default: 5,
  },
});

const emit = defineEmits(['reviewUpdated']);

const router = useRouter();
const expanded = ref(false);

const truncatedContent = computed(() => {
  if (!props.review?.comments) return "";

  const content = props.review.comments;
  const lines = content.split("\n");

  if (expanded.value || lines.length <= props.maxLines) {
    return content;
  }

  return lines.slice(0, props.maxLines).join("\n") + "\n\n...";
});

const needsTruncation = computed(() => {
  return props.review?.comments?.split("\n").length > props.maxLines;
});

const handleVote = async (reviewId, isKudos) => {
  if (!props.isAuthenticated) {
    if (confirm("Please login to vote on reviews!")) {
      router.push("/accounts/login");
    }
    return;
  }

  try {
    const response = await fetch(`/api/review/${reviewId}/vote/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ is_kudos: isKudos }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    // Emit event to parent so it can update the review data
    emit('reviewUpdated', {
      reviewId,
      kudos_count: data.kudos_count,
      dislike_count: data.dislike_count,
      user_vote: data.user_vote,
    });
  } catch (e) {
    console.error("Error voting on review:", e);
    alert("Error voting on review. Please try again.");
  }
};

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
</script>

<style scoped>
@import "../styles/MarkdownContent.css";
</style>
