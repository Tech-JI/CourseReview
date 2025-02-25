import { createApp } from "vue";
import App from "./App.vue";
import { createRouter, createWebHistory } from "vue-router";
import "./style.css";

const routes = [
  { path: "/course/:course_id", component: App, props: true },
  // Add other routes as you convert more pages
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

const app = createApp(App);
app.use(router);
app.mount("#app");
