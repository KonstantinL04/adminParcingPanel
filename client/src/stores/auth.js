import { defineStore } from "pinia";
import axios from "axios";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null,
    initialized: false,
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
  },

  actions: {
    async initSession() {
      try {
        await axios.get("/api/accounts/auth/csrf/");
        const { data } = await axios.get("/api/accounts/auth/me/");
        this.user = data.user;
      } catch {
        this.user = null;
      } finally {
        this.initialized = true;
      }
    },

    async login(identifier, password) {
      await axios.get("/api/accounts/auth/csrf/");
      const payload = identifier.includes("@")
        ? { email: identifier, password }
        : { username: identifier, password };
      const { data } = await axios.post("/api/accounts/auth/login/", payload);
      this.user = data.user;
      return data.user;
    },

    async logout() {
      try {
        await axios.post("/api/accounts/auth/logout/");
      } finally {
        this.user = null;
      }
    },
  },
});
