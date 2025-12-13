<script setup>
import { useRouter } from "vue-router";

// const router = useRouter();
// const userStore = useUserStore();

// function logout() {
//   userStore.logout();
//   router.push("/login");
// }
</script>

<template>
  <div class="app-wrapper">

    <!-- Боковое меню -->
    <nav id="sidebarMenu" class="sidebar d-flex flex-column p-3 bg-light">
      <h4 class="mb-4">Панель управления</h4>

      <ul class="nav nav-pills flex-column mb-auto">

        <li class="nav-item">
          <router-link to="/parser" class="nav-link">
            <i class="bi bi-house-door-fill me-2"></i>
            Главная
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/chats" class="nav-link">
            <i class="bi bi-chat-dots-fill me-2"></i>
            Чаты
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/excluded_users" class="nav-link">
            <i class="bi bi-person-x-fill me-2"></i> Исключённые пользователи
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/alert_categories" class="nav-link">
            <i class="bi bi-car-front-fill me-2"></i> Категории
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/locations" class="nav-link">
            <i class="bi bi-map-fill me-2"></i> Словарь мест
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/routes" class="nav-link">
            <i class="bi bi-sign-turn-slight-right-fill me-2"></i> Маршруты
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/settings" class="nav-link">
            <i class="bi bi-gear-fill me-2"></i> Настройки
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/settings_api" class="nav-link">
            <i class="bi bi-key-fill me-2"></i> API-настройки
          </router-link>
        </li>
      </ul>

      <hr />

      <div class="dropdown">
        <a class="d-flex align-items-center link-dark text-decoration-none dropdown-toggle" data-bs-toggle="dropdown"
          aria-expanded="false" href="#">
          <i class="bi bi-person-circle fs-5 me-2"></i>
          Пользователь
        </a>
        <ul class="dropdown-menu text-small shadow">
          <li><a class="dropdown-item" href="/admin">Админка</a></li>
        </ul>
      </div>

      <div class="mt-3">
        <button class="btn btn-secondary w-100" @click="logout">
          <i class="bi bi-door-closed-fill"></i> Выйти
        </button>
      </div>
    </nav>

    <!-- Основной контент -->
    <main class="main-content p-4">
      <router-view />
    </main>

  </div>
</template>

<style scoped>
.app-wrapper {
  display: flex;
  min-height: 100vh;
}

/* Sidebar */
.sidebar {
  width: 250px;
  min-height: 100vh;
  border-right: 1px solid #ddd;
}

/* Основной контент */
.main-content {
  flex-grow: 1;
}

/* Активный пункт меню bootstrap */
.nav-link.router-link-active {
  background-color: #0d6efd;
  color: white !important;
}

.nav-link {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  color: #333;
}

.nav-link:hover {
  background: #e7e7e7;
  color: #000;
}
</style>