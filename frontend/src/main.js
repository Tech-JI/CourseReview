import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import CourseDetail from "./components/CourseDetail.vue";
import Departments from "./components/Departments.vue";
import CourseSearch from "./components/CourseSearch.vue";
import "./style.css";

const routes = [
  { path: "/course/:course_id", component: CourseDetail, props: true },
  { path: "/departments", component: Departments },
  { path: "/search", component: CourseSearch, props: (route) => ({ query: route.query.q }) },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

const app = createApp(App);
app.use(router);
app.mount("#app");
