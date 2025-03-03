import { createApp } from "vue";
import CourseDetail from "./components/CourseDetail.vue";
import { createRouter, createWebHistory } from "vue-router";
import "./style.css";

const routes = [
  { path: "/course/:course_id", component: CourseDetail, props: true },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

const app = createApp(CourseDetail);
app.use(router);
app.mount("#app");
