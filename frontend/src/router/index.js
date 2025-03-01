import { createRouter, createWebHashHistory } from "vue-router";
import CourseDetail from "../components/CourseDetail.vue";

const routes = [
  {
    path: "/course/:course_id",
    name: "CourseDetail",
    component: CourseDetail,
  },
  // Add other routes as needed
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
