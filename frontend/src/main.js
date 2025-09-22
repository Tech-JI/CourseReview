import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import Login from "./views/Login.vue";
import CourseDetail from "./views/CourseDetail.vue";
import Landing from "./views/Home.vue";
import CourseReviewSearch from "./views/CourseReviewSearch.vue";
import CourseList from "./components/CourseList.vue";
import AuthCallback from "./views/AuthCallback.vue";
import Signup from "./views/Signup.vue";
import ResetPassword from "./views/ResetPassword.vue";
import "./style.css";

const routes = [
  { path: "/", component: Landing },
  { path: "/login", component: Login },
  { path: "/accounts/login", component: Login }, // Legacy route for backward compatibility
  { path: "/signup", component: Signup },
  { path: "/accounts/signup", component: Signup },
  { path: "/reset", component: ResetPassword },
  { path: "/accounts/reset", component: ResetPassword },
  { path: "/callback", component: AuthCallback },
  { path: "/course/:course_id", component: CourseDetail, props: true },
  {
    path: "/course/:courseId/review_search",
    component: CourseReviewSearch,
    props: true,
  },
  {
    path: "/courses",
    component: CourseList,
    props: (route) => ({ queryParams: route.query }),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

const app = createApp(App);
app.use(router);
app.mount("#app");
