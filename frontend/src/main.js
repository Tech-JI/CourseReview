import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import CourseDetail from "./components/CourseDetail.vue";
import Departments from "./components/Departments.vue";
import CourseSearch from "./components/CourseSearch.vue";
import Landing from "./components/Landing.vue";
import CourseReviewSearch from "./components/CourseReviewSearch.vue"; // Import
import "./style.css";

const routes = [
  { path: "/", component: Landing },
  { path: "/course/:course_id", component: CourseDetail, props: true },
  { path: "/departments", component: Departments },
  { path: "/search", component: CourseSearch, props: (route) => ({ query: route.query.q }) },
  { path: '/course/:courseId/review_search', component: CourseReviewSearch, props: true }, // Add route

];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

const app = createApp(App);
app.use(router);
app.mount("#app");
