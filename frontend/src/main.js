import { createApp } from "vue";
import App from "./App.vue";
import { createRouter, createWebHashHistory } from "vue-router";
import "./style.css";

const routes = [
  { path: "/course/:course_id", component: App, props: true },
  // Add other routes as you convert more pages
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

const app = createApp(App);
app.use(router);
app.mount("#app");
