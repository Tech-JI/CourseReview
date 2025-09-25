<template>
  <div class="pagination-container">
    <div class="space-y-6">
      <ReviewCard
        v-for="review in paginatedReviews"
        :key="review.id"
        :review="review"
        :is-authenticated="isAuthenticated"
        :sanitize="sanitize"
        :max-lines="maxLines"
        @review-updated="handleReviewUpdate"
      />
    </div>

    <div v-if="reviews.length === 0" class="text-center py-8">
      <p class="text-gray-500">No reviews found.</p>
    </div>

    <div
      class="mt-8 flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6"
    >
      <div class="flex flex-1 justify-between sm:hidden">
        <button
          :disabled="currentPage === 1"
          :class="[
            'relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium',
            currentPage === 1
              ? 'text-gray-300 cursor-not-allowed'
              : 'text-gray-700 hover:bg-gray-50',
          ]"
          @click="goToPage(currentPage - 1)"
        >
          Previous
        </button>
        <button
          :disabled="currentPage === totalPages || totalPages === 0"
          :class="[
            'relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium',
            currentPage === totalPages || totalPages === 0
              ? 'text-gray-300 cursor-not-allowed'
              : 'text-gray-700 hover:bg-gray-50',
          ]"
          @click="goToPage(currentPage + 1)"
        >
          Next
        </button>
      </div>

      <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
        <div>
          <p class="text-sm text-gray-700">
            Showing
            <span class="font-medium">{{ displayStartIndex }}</span>
            to
            <span class="font-medium">{{ displayEndIndex }}</span>
            of
            <span class="font-medium">total {{ reviews.length }}</span>
            results
          </p>
        </div>

        <div v-if="totalPages > 0">
          <nav
            class="isolate inline-flex -space-x-px rounded-md shadow-xs"
            aria-label="Pagination"
          >
            <button
              :disabled="currentPage === 1"
              :class="[
                'relative inline-flex items-center rounded-l-md px-2 py-2 ring-1 ring-gray-300 ring-inset focus:z-20 focus:outline-offset-0',
                currentPage === 1
                  ? 'text-gray-300 cursor-not-allowed'
                  : 'text-gray-400 hover:bg-gray-50',
              ]"
              @click="goToPage(currentPage - 1)"
            >
              <span class="sr-only">Previous</span>
              <ChevronLeftIcon class="size-5" aria-hidden="true" />
            </button>

            <template v-for="page in visiblePages" :key="page">
              <span
                v-if="page === '...'"
                class="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-700 ring-1 ring-gray-300 ring-inset focus:outline-offset-0"
              >
                ...
              </span>
              <button
                v-else
                :class="[
                  'relative inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20',
                  page === currentPage
                    ? 'z-10 bg-indigo-600 text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600'
                    : 'text-gray-900 ring-1 ring-gray-300 ring-inset hover:bg-gray-50 focus:outline-offset-0',
                ]"
                :aria-current="page === currentPage ? 'page' : undefined"
                @click="goToPage(page)"
              >
                {{ page }}
              </button>
            </template>

            <button
              :disabled="currentPage === totalPages || totalPages === 0"
              :class="[
                'relative inline-flex items-center rounded-r-md px-2 py-2 ring-1 ring-gray-300 ring-inset focus:z-20 focus:outline-offset-0',
                currentPage === totalPages || totalPages === 0
                  ? 'text-gray-300 cursor-not-allowed'
                  : 'text-gray-400 hover:bg-gray-50',
              ]"
              @click="goToPage(currentPage + 1)"
            >
              <span class="sr-only">Next</span>
              <ChevronRightIcon class="size-5" aria-hidden="true" />
            </button>
          </nav>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/vue/20/solid";
import ReviewCard from "./ReviewCard.vue";

const props = defineProps({
  reviews: {
    type: Array,
    required: true,
  },
  isAuthenticated: {
    type: Boolean,
    required: true,
  },
  sanitize: {
    type: Function,
    required: true,
  },
  maxLines: {
    type: Number,
    default: 5,
  },
  pageSize: {
    type: Number,
    default: 10,
  },
});

const emit = defineEmits(["reviewUpdated"]);

const currentPage = ref(1);

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(props.reviews.length / props.pageSize));
});

const startIndex = computed(() => {
  return (currentPage.value - 1) * props.pageSize;
});

const endIndex = computed(() => {
  return startIndex.value + props.pageSize;
});

const displayStartIndex = computed(() => {
  return props.reviews.length === 0 ? 0 : startIndex.value + 1;
});

const displayEndIndex = computed(() => {
  return Math.min(endIndex.value, props.reviews.length);
});

const paginatedReviews = computed(() => {
  return props.reviews.slice(startIndex.value, endIndex.value);
});

const visiblePages = computed(() => {
  const total = totalPages.value;
  const current = currentPage.value;
  const delta = 2;

  if (total <= 1) {
    return [1];
  }

  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages = [];

  pages.push(1);

  if (current - delta > 2) {
    pages.push("...");
  }

  const start = Math.max(2, current - delta);
  const end = Math.min(total - 1, current + delta);

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  if (current + delta < total - 1) {
    pages.push("...");
  }

  if (total > 1 && !pages.includes(total)) {
    pages.push(total);
  }

  return pages;
});

const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
  }
};

const handleReviewUpdate = (updateData) => {
  emit("reviewUpdated", updateData);
};

watch([() => props.reviews, totalPages], ([, newTotalPages]) => {
  if (currentPage.value > newTotalPages) {
    currentPage.value = Math.max(1, newTotalPages);
  }
});
</script>

<style scoped>
.pagination-container {
  width: 100%;
}
</style>
