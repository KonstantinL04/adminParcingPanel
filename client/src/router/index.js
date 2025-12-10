import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue';
import ExcludedUserView from '../views/ExcludedUserView.vue';
import EmojiGroupView from '../views/EmojiGroupView.vue';
import TextPatternView from '../views/TextPatternView.vue';
import LocationView from '../views/LocationView.vue';
import SettingView from '../views/SettingView.vue';
import SettingAPIView from '../views/SettingAPIView.vue';

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
      path: "/emoji_groups",
      name: "EmojiGroupView",
      component: EmojiGroupView
    },
    {
      path: "/text_patterns",
      name: "TextPatternView",
      component: TextPatternView
    },
    {
      path: "/locations",
      name: "LocationView",
      component: LocationView
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
  ],
})

export default router
