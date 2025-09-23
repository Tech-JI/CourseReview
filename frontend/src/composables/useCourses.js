import { ref, reactive } from "vue";

export function useCourses() {
  const courses = ref([]);
  const departments = ref([]);
  const loading = ref(false);
  const error = ref(null);

  const pagination = reactive({
    current_page: 1,
    total_pages: 1,
    total_courses: 0,
    limit: 20,
  });

  const filters = reactive({
    department: "",
    code: "",
    min_quality: null,
    min_difficulty: null,
  });

  const sorting = reactive({
    sort_by: "course_code",
    sort_order: "asc",
  });

  const fetchDepartments = async () => {
    try {
      const response = await fetch("/api/departments/");
      if (!response.ok) throw new Error("Failed to fetch departments");
      departments.value = await response.json();
    } catch (e) {
      console.error("useCourses: Error fetching departments:", e);
    }
  };

  const fetchCourses = async (isAuth = false) => {
    loading.value = true;
    error.value = null;

    const params = new URLSearchParams();
    if (filters.department) params.append("department", filters.department);
    if (filters.code) params.append("code", filters.code.trim());
    if (filters.min_quality && isAuth)
      params.append("min_quality", filters.min_quality);
    params.append("sort_by", sorting.sort_by);
    params.append("sort_order", sorting.sort_order);
    params.append("page", pagination.current_page);

    try {
      const response = await fetch(`/api/courses/?${params.toString()}`);
      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: "Unknown error" }));
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`,
        );
      }
      const data = await response.json();
      courses.value = data.courses;
      pagination.current_page = data.pagination.current_page;
      pagination.total_pages = data.pagination.total_pages;
      pagination.total_courses = data.pagination.total_courses;
      pagination.limit = data.pagination.limit;
    } catch (e) {
      console.error("useCourses: Error fetching courses:", e);
      error.value = e.message;
      courses.value = [];
    } finally {
      loading.value = false;
    }
  };

  const getQueryObject = (isAuth = false) => {
    const query = {};
    if (filters.department) query.department = filters.department;
    if (filters.code) query.code = filters.code.trim();
    if (filters.min_quality && isAuth) query.min_quality = filters.min_quality;
    if (sorting.sort_by !== "course_code" || sorting.sort_order !== "asc") {
      query.sort_by = sorting.sort_by;
      query.sort_order = sorting.sort_order;
    }
    if (pagination.current_page > 1) query.page = pagination.current_page;
    return query;
  };

  const applyFiltersAndSort = () => {
    pagination.current_page = 1;
  };

  const resetFiltersAndSort = () => {
    filters.department = "";
    filters.code = "";
    filters.min_quality = null;
    filters.min_difficulty = null;
    sorting.sort_by = "course_code";
    sorting.sort_order = "asc";
    pagination.current_page = 1;
  };

  const changePage = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      pagination.current_page = newPage;
    }
  };

  const syncStateFromQuery = (query) => {
    filters.department = query.department || "";
    filters.code = query.code || "";
    filters.min_quality = query.min_quality
      ? parseInt(query.min_quality, 10)
      : null;
    sorting.sort_by = query.sort_by || "course_code";
    sorting.sort_order = query.sort_order || "asc";
    pagination.current_page = query.page ? parseInt(query.page, 10) : 1;

    // Ensure sort_by is valid if auth state changes will be handled by caller
    if (!filters.min_quality) {
      // noop
    }
  };

  return {
    courses,
    departments,
    loading,
    error,
    pagination,
    filters,
    sorting,
    fetchDepartments,
    fetchCourses,
    getQueryObject,
    applyFiltersAndSort,
    resetFiltersAndSort,
    changePage,
    syncStateFromQuery,
  };
}

export default { useCourses };
