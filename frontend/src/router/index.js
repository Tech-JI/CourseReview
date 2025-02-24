import { createRouter, createWebHistory } from "vue-router";
import CourseDetail from "../views/CourseDetail.vue";

const routes = [
  {
    path: "/courses/:id",
    component: CourseDetail,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
