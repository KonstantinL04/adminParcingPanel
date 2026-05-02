import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue';
import ExcludedUserView from '../views/ExcludedUserView.vue';
import AlertCategoryView from '../views/AlertCategoryView.vue';
import RouteView from '../views/RouteView.vue';
import LocationView from '../views/LocationView.vue';
import SettingView from '../views/SettingView.vue';
import SettingAPIView from '../views/SettingAPIView.vue';
import ParserView from '../views/ParserView.vue';
import NlpTrainView from '../views/NlpTrainView.vue';
import EventsMapView from '../views/EventsMapView.vue';
import PocketGisView from '../views/PocketGisView.vue';
import RegionsPolygonView from '../views/RegionsPolygonView.vue';
import PocketGisCategoriesView from '../views/PocketGisCategoriesView.vue';
import ZonePreviewView from '../views/ZonePreviewView.vue';
import LoginView from "../views/LoginView.vue";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/login",
      name: "LoginView",
      component: LoginView,
      meta: { requiresAuth: false },
    },
    {
      path: "/chats",
      name: "ChatView",
      component: ChatView,
      meta: { requiresAuth: true },
    },
    {
      path: "/excluded_users",
      name: "ExcludedUserView",
      component: ExcludedUserView,
      meta: { requiresAuth: true },
    },
    {
      path: "/alert_categories",
      name: "AlertCategoryView",
      component: AlertCategoryView,
      meta: { requiresAuth: true },
    },
    {
      path: "/locations",
      name: "LocationView",
      component: LocationView,
      meta: { requiresAuth: true },
    },
    {
      path: "/routes",
      name: "RouteView",
      component: RouteView,
      meta: { requiresAuth: true },
    },
    {
      path: "/settings",
      name: "SettingView",
      component: SettingView,
      meta: { requiresAuth: true },
    },
    {
      path: "/settings_api",
      name: "SettingAPIView",
      component: SettingAPIView,
      meta: { requiresAuth: true },
    },
    {
      path: "/parser",
      name: "ParserView",
      component: ParserView,
      meta: { requiresAuth: true },
    },
    {
      path: "/events-map",
      name: "EventsMapView",
      component: EventsMapView,
      meta: { requiresAuth: true },
    },
    {
      path: "/pocketgis",
      name: "PocketGisView",
      component: PocketGisView,
      meta: { requiresAuth: true },
    },
    {
      path: "/regions-polygons",
      name: "RegionsPolygonView",
      component: RegionsPolygonView,
      meta: { requiresAuth: true },
    },
    {
      path: "/pocketgis-categories",
      name: "PocketGisCategoriesView",
      component: PocketGisCategoriesView,
      meta: { requiresAuth: true },
    },
    {
      path: "/zone-preview",
      name: "ZonePreviewView",
      component: ZonePreviewView,
      meta: { requiresAuth: true },
    },
    {
      path: "/nlp",
      name: "NlpTrainView",
      component: NlpTrainView,
      meta: { requiresAuth: true },
    },
    { path: "/:pathMatch(.*)*", redirect: "/parser" },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  const requiresAuth = to.meta.requiresAuth !== false;

  if (!auth.initialized) {
    await auth.initSession();
  }

  if (requiresAuth && !auth.isAuthenticated) {
    return { path: "/login", query: { next: to.fullPath } };
  }

  if (to.path === "/login" && auth.isAuthenticated) {
    return "/parser";
  }
});

export default router
