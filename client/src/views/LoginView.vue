<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();

const identifier = ref("");
const password = ref("");
const isLoading = ref(false);
const errorText = ref("");

async function submitLogin() {
  errorText.value = "";
  isLoading.value = true;
  try {
    await auth.login(identifier.value.trim(), password.value);
    router.push("/parser");
  } catch (err) {
    errorText.value = err?.response?.data?.detail || "Не удалось выполнить вход";
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="login-page d-flex align-items-center justify-content-center">
    <div class="card shadow-sm login-card">
      <div class="card-body p-4">
        <h4 class="mb-3">Вход в панель</h4>
        <p class="text-muted mb-4">Используйте email или username</p>

        <form @submit.prevent="submitLogin">
          <div class="mb-3">
            <label class="form-label">Email / Username</label>
            <input
              v-model="identifier"
              type="text"
              class="form-control"
              autocomplete="username"
              required
            />
          </div>

          <div class="mb-3">
            <label class="form-label">Пароль</label>
            <input
              v-model="password"
              type="password"
              class="form-control"
              autocomplete="current-password"
              required
            />
          </div>

          <div v-if="errorText" class="alert alert-danger py-2">{{ errorText }}</div>

          <button class="btn btn-primary w-100" :disabled="isLoading">
            {{ isLoading ? "Входим..." : "Войти" }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background: #f5f7fb;
}

.login-card {
  width: 100%;
  max-width: 420px;
}
</style>
