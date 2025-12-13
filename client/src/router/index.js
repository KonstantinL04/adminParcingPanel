import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue';
import ExcludedUserView from '../views/ExcludedUserView.vue';
import AlertCategoryView from '../views/AlertCategoryView.vue';
import RouteView from '../views/RouteView.vue';
import LocationView from '../views/LocationView.vue';
import SettingView from '../views/SettingView.vue';
import SettingAPIView from '../views/SettingAPIView.vue';
import ParserView from '../views/ParserView.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/chats",
      name: "ChatView",
      component: ChatView
    },
    {
      path: "/excluded_users",
      name: "ExcludedUserView",
      component: ExcludedUserView
    },
    {
      path: "/alert_categories",
      name: "AlertCategoryView",
      component: AlertCategoryView
    },
    {
      path: "/locations",
      name: "LocationView",
      component: LocationView
    },
    {
      path: "/routes",
      name: "RouteView",
      component: RouteView
    },
    {
      path: "/settings",
      name: "SettingView",
      component: SettingView
    },
    {
      path: "/settings_api",
      name: "SettingAPIView",
      component: SettingAPIView
    },
    {
      path: "/parser",
      name: "ParserView",
      component: ParserView
    },
  ],
})

export default router
