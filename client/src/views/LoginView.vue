<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import appLogo from "@/assets/app.png";

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
  <div class="login-page">
    <section class="login-panel">
      <div class="brand-block">
        <div class="brand-mark">
          <img :src="appLogo" alt="Дорожный помощник" />
        </div>
        <div>
          <h1>Дорожный помощник</h1>
          <p>Панель управления</p>
        </div>
      </div>

      <div class="login-card">
        <div class="login-head">
          <h2>Вход в систему</h2>
          <p>Используйте email или username</p>
        </div>

        <form @submit.prevent="submitLogin">
          <div class="field-group">
            <label>Email / Username</label>
            <input
              v-model="identifier"
              type="text"
              class="login-input"
              autocomplete="username"
              placeholder="Введите логин"
              required
            />
          </div>

          <div class="field-group">
            <label>Пароль</label>
            <input
              v-model="password"
              type="password"
              class="login-input"
              autocomplete="current-password"
              placeholder="Введите пароль"
              required
            />
          </div>

          <div v-if="errorText" class="login-error">{{ errorText }}</div>

          <button class="login-submit" :disabled="isLoading">
            {{ isLoading ? "Входим..." : "Войти" }}
          </button>
        </form>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  background: #f4f6f9;
}

.login-panel {
  width: 100%;
  max-width: 470px;
}

.login-card {
  width: 100%;
  padding: 30px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 24px;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.12);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 22px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.85);
  border-radius: 22px;
  box-shadow: 0 18px 46px rgba(15, 23, 42, 0.08);
}

.brand-mark {
  width: 58px;
  height: 58px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  background: #f8fafc;
  border-radius: 18px;
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.95);
}

.brand-mark img {
  width: 38px;
  height: 38px;
  object-fit: contain;
}

.brand-block h1 {
  margin: 0;
  color: #111827;
  font-size: 25px;
  font-weight: 900;
  line-height: 1.08;
}

.brand-block p,
.login-head p {
  margin: 5px 0 0;
  color: #6b7280;
  font-size: 15px;
  font-weight: 650;
}

.login-head {
  margin-bottom: 24px;
}

.login-head h2 {
  margin: 0;
  color: #111827;
  font-size: 28px;
  font-weight: 900;
  letter-spacing: 0;
}

.field-group {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

.field-group label {
  color: #1f2937;
  font-size: 15px;
  font-weight: 800;
}

.login-input {
  width: 100%;
  height: 48px;
  padding: 0 15px;
  color: #111827;
  font-size: 16px;
  font-weight: 650;
  background: #fff;
  border: 1px solid #d9e1ec;
  border-radius: 14px;
  outline: none;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.login-input:focus {
  border-color: #0d6efd;
  box-shadow: 0 0 0 4px rgba(13, 110, 253, 0.12), 0 10px 24px rgba(15, 23, 42, 0.08);
}

.login-error {
  margin: 4px 0 16px;
  padding: 10px 12px;
  color: #b42318;
  font-size: 14px;
  font-weight: 750;
  background: #fff1f0;
  border: 1px solid #ffdad6;
  border-radius: 14px;
}

.login-submit {
  width: 100%;
  height: 50px;
  margin-top: 4px;
  color: #fff;
  font-size: 17px;
  font-weight: 850;
  background: #1677ff;
  border: 0;
  border-radius: 16px;
  box-shadow: 0 12px 28px rgba(22, 119, 255, 0.28);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.login-submit:hover:not(:disabled) {
  background: #0d6efd;
  box-shadow: 0 16px 34px rgba(13, 110, 253, 0.32);
  transform: translateY(-1px);
}

.login-submit:disabled {
  cursor: wait;
  opacity: 0.72;
}

@media (max-width: 520px) {
  .login-card {
    padding: 24px;
    border-radius: 20px;
  }

  .brand-block {
    padding: 14px;
    border-radius: 20px;
  }

  .brand-block h1 {
    font-size: 21px;
  }

  .login-head h2 {
    font-size: 24px;
  }
}
</style>
