<template>
  <div class="bg-white">
    <!-- Hero section -->
    <div class="relative isolate px-6 pt-14 lg:px-8">
      <div
        class="absolute inset-x-0 -top-40 -z-10 transform-gpu overflow-hidden blur-3xl sm:-top-80"
        aria-hidden="true"
      >
        <div
          class="relative left-[calc(50%-11rem)] aspect-[1155/678] w-[36.125rem] -translate-x-1/2 rotate-[30deg] bg-gradient-to-tr from-[#ff80b5] to-[#9089fc] opacity-30 sm:left-[calc(50%-30rem)] sm:w-[72.1875rem]"
          style="
            clip-path: polygon(
              74.1% 44.1%,
              100% 61.6%,
              97.5% 26.9%,
              85.5% 0.1%,
              80.7% 2%,
              72.5% 32.5%,
              60.2% 62.4%,
              52.4% 68.1%,
              47.5% 58.3%,
              45.2% 34.5%,
              27.5% 76.7%,
              0.1% 64.9%,
              17.9% 100%,
              27.6% 76.8%,
              76.1% 97.7%,
              74.1% 44.1%
            );
          "
        ></div>
      </div>

      <div class="mx-auto max-w-2xl py-32 sm:py-48 lg:py-56">
        <div class="text-center">
          <h1
            class="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl"
          >
            JI Course Review
          </h1>
          <p class="mt-6 text-lg leading-8 text-gray-600">
            UMJI Course Reviews, Rankings, and Recommendations
          </p>
          <p class="mt-2 text-base text-gray-500">
            {{ reviewCount.toLocaleString() }} reviews and counting
          </p>

          <!-- Search section -->
          <div class="mt-10">
            <div class="mx-auto max-w-md">
              <label for="search" class="sr-only">Search for courses</label>
              <div class="relative">
                <div
                  class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3"
                >
                  <MagnifyingGlassIcon
                    class="h-5 w-5 text-gray-400"
                    aria-hidden="true"
                  />
                </div>
                <input
                  id="search"
                  name="search"
                  type="search"
                  v-model="searchQuery"
                  @keyup.enter="performSearch"
                  class="block w-full rounded-md border-0 bg-white py-3 pl-10 pr-3 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                  placeholder="Search for courses..."
                />
              </div>
              <button
                @click="performSearch"
                class="mt-4 w-full rounded-md bg-indigo-600 px-3.5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
              >
                Search Courses
              </button>
            </div>
          </div>

          <!-- Action buttons -->
          <div class="mt-10 flex items-center justify-center gap-x-6">
            <button
              @click="goToBestClasses"
              class="rounded-md bg-white px-3.5 py-2.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
            >
              Best Classes
            </button>
            <button
              @click="goToLayups"
              class="rounded-md bg-white px-3.5 py-2.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
            >
              Layups {{ !isAuthenticated ? "(login required)" : "" }}
            </button>
            <button
              @click="goToDepartments"
              class="rounded-md bg-white px-3.5 py-2.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
            >
              Browse All
            </button>
          </div>
        </div>
      </div>

      <div
        class="absolute inset-x-0 top-[calc(100%-13rem)] -z-10 transform-gpu overflow-hidden blur-3xl sm:top-[calc(100%-30rem)]"
        aria-hidden="true"
      >
        <div
          class="relative left-[calc(50%+3rem)] aspect-[1155/678] w-[36.125rem] -translate-x-1/2 bg-gradient-to-tr from-[#ff80b5] to-[#9089fc] opacity-30 sm:left-[calc(50%+36rem)] sm:w-[72.1875rem]"
          style="
            clip-path: polygon(
              74.1% 44.1%,
              100% 61.6%,
              97.5% 26.9%,
              85.5% 0.1%,
              80.7% 2%,
              72.5% 32.5%,
              60.2% 62.4%,
              52.4% 68.1%,
              47.5% 58.3%,
              45.2% 34.5%,
              27.5% 76.7%,
              0.1% 64.9%,
              17.9% 100%,
              27.6% 76.8%,
              76.1% 97.7%,
              74.1% 44.1%
            );
          "
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { MagnifyingGlassIcon } from "@heroicons/vue/24/outline";
import { useAuth } from "../composables/useAuth";

const router = useRouter();
const reviewCount = ref(0);
const { isAuthenticated } = useAuth();
const searchQuery = ref("");

onMounted(async () => {
  await fetchLandingData();
  // useAuth performs initial authentication check
});

const fetchLandingData = async () => {
  try {
    const response = await fetch("/api/landing/");
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    reviewCount.value = data.review_count;
  } catch (error) {
    console.error("Error fetching landing data:", error);
  }
};

// Authentication checking handled via shared util

const performSearch = () => {
  if (searchQuery.value.trim().length >= 2) {
    router.push({
      path: "/courses", // Navigate to the new courses page
      query: { code: searchQuery.value.trim().toUpperCase() }, // Use 'code' query param
    });
  } else {
    alert("Search query must be at least 2 characters long");
  }
};

const goToBestClasses = () => {
  router.push({
    path: "/courses",
    query: { sort_by: "quality_score", sort_order: "desc" },
  });
};

const goToLayups = () => {
  router.push({
    path: "/courses",
    query: { sort_by: "difficulty_score", sort_order: "desc" },
  });
};

const goToDepartments = () => {
  router.push("/courses"); // Simply go to the main courses page
};
</script>
