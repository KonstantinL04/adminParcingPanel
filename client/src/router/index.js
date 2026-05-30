import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue';
import ExcludedUserView from '../views/ExcludedUserView.vue';
import AlertCategoryView from '../views/AlertCategoryView.vue';
import RouteView from '../views/RouteView.vue';
import LocationView from '../views/LocationView.vue';
import SettingAPIView from '../views/SettingAPIView.vue';
import ParserView from '../views/ParserView.vue';
import NlpTrainView from '../views/NlpTrainView.vue';
import PocketGisView from '../views/PocketGisView.vue';
import RegionsPolygonView from '../views/RegionsPolygonView.vue';
import MapView from '../views/MapView.vue';
import HelpRequestsView from '../views/HelpRequestsView.vue';
import EventClassificationView from '../views/EventClassificationView.vue';
import ModerationView from '../views/ModerationView.vue';
import UsersView from '../views/UsersView.vue';
import UserRolesView from '../views/UserRolesView.vue';
import ReputationRulesView from '../views/ReputationRulesView.vue';
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
      path: "/categories",
      name: "EventCategoriesView",
      component: EventClassificationView,
      meta: { requiresAuth: true },
    },
    {
      path: "/parsing-categories",
      name: "ParsingCategoriesView",
      component: AlertCategoryView,
      meta: { requiresAuth: true },
    },
    { path: "/alert_categories", redirect: "/parsing-categories" },
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
    { path: "/pocketgis-categories", redirect: "/categories" },
    {
      path: "/map-view",
      name: "MapView",
      component: MapView,
      meta: { requiresAuth: true },
    },
    {
      path: "/nlp",
      name: "NlpTrainView",
      component: NlpTrainView,
      meta: { requiresAuth: true },
    },
    {
      path: "/help-requests",
      name: "HelpRequestsView",
      component: HelpRequestsView,
      meta: { requiresAuth: true },
    },
    {
      path: "/moderation",
      name: "ModerationView",
      component: ModerationView,
      meta: { requiresAuth: true, requiresRole: ["moderator", "admin"] },
    },
    {
      path: "/users",
      name: "UsersView",
      component: UsersView,
      meta: { requiresAuth: true, requiresRole: ["admin"] },
    },
    {
      path: "/user-roles",
      name: "UserRolesView",
      component: UserRolesView,
      meta: { requiresAuth: true, requiresSuperuser: true },
    },
    {
      path: "/reputation-rules",
      name: "ReputationRulesView",
      component: ReputationRulesView,
      meta: { requiresAuth: true, requiresRole: ["admin"] },
    },
    { path: "/event-classification", redirect: "/categories" },
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

  const roles = new Set(auth.user?.roles || []);
  const isFullAdmin = auth.user?.is_superuser || roles.has("admin");
  const isModeratorOnly =
    auth.isAuthenticated &&
    !isFullAdmin &&
    (auth.user?.is_staff || roles.has("moderator"));
  const moderatorAllowedPaths = new Set(["/map-view", "/moderation"]);

  if (isModeratorOnly && requiresAuth && !moderatorAllowedPaths.has(to.path)) {
    return "/map-view";
  }

  const requiredRoles = to.meta.requiresRole;
  if (requiredRoles && requiredRoles.length) {
    const isPrivileged = isFullAdmin;
    const allowedAsStaffModerator = auth.user?.is_staff && requiredRoles.includes("moderator");
    const allowed = isPrivileged || allowedAsStaffModerator || requiredRoles.some((r) => roles.has(r));
    if (!allowed) {
      return "/map-view";
    }
  }

  if (to.meta.requiresSuperuser && !isFullAdmin) {
    return "/map-view";
  }

  if (to.path === "/login" && auth.isAuthenticated) {
    return "/parser";
  }
});

export default router
