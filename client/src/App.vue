<script setup>
import { useRouter, useRoute } from "vue-router";
import { computed, ref, watch } from "vue";
import { useAuthStore } from "@/stores/auth";
import defaultEventIcon from "@/assets/app.png";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const showShell = computed(() => route.path !== "/login");
const showLogoutModal = ref(false);

function openLogoutModal() {
  showLogoutModal.value = true;
}

function closeLogoutModal() {
  showLogoutModal.value = false;
}

async function confirmLogout() {
  await auth.logout();
  router.push("/login");
}

function closeMobileMenu() {
  const navbar = document.getElementById("navbarNav");
  if (navbar && navbar.classList.contains("show")) {
    navbar.classList.remove("show");
  }
  document.querySelectorAll(".dropdown-menu.show").forEach(el => {
    el.classList.remove("show");
  });
}

watch(() => route.path, () => {
  closeMobileMenu();
});
</script>

<template>
  <router-view v-if="!showShell" />

  <div v-else class="app-wrapper">

    <!-- NAVBAR -->
    <nav class="navbar navbar-expand-lg navbar-custom border-bottom shadow-sm">
      <div class="container-fluid navbar-safe">

        <!-- logo -->
        <router-link to="/zone-preview" class="navbar-brand brand-title d-flex align-items-center gap-2">
          <img :src="defaultEventIcon" class="brand-icon" alt="logo" />
          Дорожный помощник
        </router-link>

        <!-- mobile toggler — явно справа -->
        <button class="navbar-toggler ms-auto" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>

        <div class="collapse navbar-collapse" id="navbarNav">

          <!-- center menu -->
          <ul class="navbar-nav mx-auto align-items-center gap-2 main-nav-center">

            <!-- карта -->
            <li class="nav-item">
              <router-link to="/zone-preview" class="nav-link top-link">
                <i class="bi bi-map me-2"></i>
                Карта
              </router-link>
            </li>

            <!-- парсер -->
            <li class="nav-item dropdown main-dropdown">
              <a href="#" class="nav-link dropdown-toggle top-link" data-bs-toggle="dropdown">
                <i class="bi bi-cpu me-2"></i>
                Парсер
              </a>

              <ul class="dropdown-menu dropdown-menu-end custom-menu shadow border-0">

                <li>
                  <router-link to="/parser" class="dropdown-item">
                    <i class="bi bi-sliders me-2"></i>
                    Управление парсером
                  </router-link>
                </li>

                <li>
                  <router-link to="/chats" class="dropdown-item">
                    <i class="bi bi-chat-dots-fill me-2"></i>
                    Чаты
                  </router-link>
                </li>

                <li>
                  <router-link to="/excluded_users" class="dropdown-item">
                    <i class="bi bi-person-x-fill me-2"></i>
                    Исключённые пользователи
                  </router-link>
                </li>

                <li>
                  <router-link to="/parsing-categories" class="dropdown-item">
                    <i class="bi bi-car-front-fill me-2"></i>
                    Категории парсинга
                  </router-link>
                </li>

                <li>
                  <router-link to="/locations" class="dropdown-item">
                    <i class="bi bi-geo-alt-fill me-2"></i>
                    Словарь мест
                  </router-link>
                </li>

                <li>
                  <router-link to="/routes" class="dropdown-item">
                    <i class="bi bi-sign-turn-right-fill me-2"></i>
                    Маршруты
                  </router-link>
                </li>

                <li>
                  <router-link to="/nlp" class="dropdown-item">
                    <i class="bi bi-cpu-fill me-2"></i>
                    Дообучение NLP
                  </router-link>
                </li>

                <li>
                  <hr class="dropdown-divider">
                </li>

                <li>
                  <router-link to="/settings" class="dropdown-item">
                    <i class="bi bi-gear-fill me-2"></i>
                    Настройки
                  </router-link>
                </li>

                <li>
                  <router-link to="/settings_api" class="dropdown-item">
                    <i class="bi bi-key-fill me-2"></i>
                    API-настройки
                  </router-link>
                </li>

              </ul>
            </li>

            <!-- статичные события -->
            <li class="nav-item dropdown main-dropdown">
              <a href="#" class="nav-link dropdown-toggle top-link" data-bs-toggle="dropdown">
                <i class="bi bi-pin-map me-2"></i>
                Статичные события
              </a>

              <ul class="dropdown-menu dropdown-menu-end custom-menu shadow border-0">

                <li>
                  <router-link to="/pocketgis" class="dropdown-item">
                    <i class="bi bi-upload me-2"></i>
                    Импорт событий
                  </router-link>
                </li>

                <li>
                  <router-link to="/regions-polygons" class="dropdown-item">
                    <i class="bi bi-bounding-box me-2"></i>
                    Полигоны областей
                  </router-link>
                </li>

                <li>
                  <router-link to="/categories" class="dropdown-item">
                    <i class="bi bi-grid-fill me-2"></i>
                    Категории
                  </router-link>
                </li>

                <li>
                  <router-link to="/help-requests" class="dropdown-item">
                    <i class="bi bi-life-preserver me-2"></i>
                    Взаимопомощь
                  </router-link>
                </li>

                <li>
                  <router-link to="/categories" class="dropdown-item">
                    <i class="bi bi-diagram-3-fill me-2"></i>
                    Классификация событий
                  </router-link>
                </li>

              </ul>
            </li>

            <li class="nav-item dropdown main-dropdown">
              <a href="#" class="nav-link dropdown-toggle top-link" data-bs-toggle="dropdown">
                <i class="bi bi-person-bounding-box"></i>
                Управление пользователями
              </a>

              <ul class="dropdown-menu dropdown-menu-end custom-menu shadow border-0">

                <li>
                  <router-link to="/pocketgis" class="dropdown-item">
                    <i class="bi bi-upload me-2"></i>
                    Импорт событий
                  </router-link>
                </li>

                <li>
                  <router-link to="/regions-polygons" class="dropdown-item">
                    <i class="bi bi-bounding-box me-2"></i>
                    Полигоны областей
                  </router-link>
                </li>

                <li>
                  <router-link to="/categories" class="dropdown-item">
                    <i class="bi bi-grid-fill me-2"></i>
                    Категории
                  </router-link>
                </li>

                <li>
                  <router-link to="/help-requests" class="dropdown-item">
                    <i class="bi bi-life-preserver me-2"></i>
                    Взаимопомощь
                  </router-link>
                </li>

                <li>
                  <router-link to="/categories" class="dropdown-item">
                    <i class="bi bi-diagram-3-fill me-2"></i>
                    Классификация событий
                  </router-link>
                </li>

              </ul>
            </li>

          </ul>

          <!-- right -->
          <div class="d-flex align-items-center gap-2">

            <!-- user -->
            <div class="dropdown main-dropdown">
              <a href="#" class="nav-link dropdown-toggle user-link" data-bs-toggle="dropdown">
                <i class="bi bi-person-circle me-2"></i>
                {{ auth.user?.email || "Пользователь" }}
              </a>

              <ul class="dropdown-menu dropdown-menu-end custom-menu shadow border-0">
                <li>
                  <a class="dropdown-item" href="/admin">
                    <i class="bi bi-shield-lock-fill me-2"></i>
                    Админка
                  </a>
                </li>
              </ul>
            </div>

            <!-- logout -->
            <button class="logout-btn" @click="openLogoutModal">
              <i class="bi bi-box-arrow-right"></i>
            </button>

          </div>

        </div>
      </div>
    </nav>

    <!-- CONTENT -->
    <main class="main-content p-4">
      <router-view />
    </main>

    <!-- custom logout modal -->
    <transition name="fade">
      <div v-if="showLogoutModal" class="modal-overlay" @click.self="closeLogoutModal">
        <div class="logout-card shadow">

          <div class="logout-icon">
            <i class="bi bi-box-arrow-right"></i>
          </div>

          <h5 class="mb-2">Выйти из аккаунта?</h5>
          <p class="text-muted mb-4">
            Текущая сессия будет завершена.
          </p>

          <div class="d-flex gap-2">
            <button class="btn-cancel flex-fill" @click="closeLogoutModal">
              Отмена
            </button>

            <button class="btn-confirm flex-fill" @click="confirmLogout">
              Выйти
            </button>
          </div>

        </div>
      </div>
    </transition>

  </div>
</template>

<style scoped>
/* ---- mobile ---- */
@media (max-width: 991.98px) {

  /* Шапка: иконка + название слева, тоглер справа — всё в одну строку */
  .navbar-safe {
    display: flex;
    flex-wrap: nowrap;
    align-items: center;
    padding-left: 14px;
    padding-right: 14px;
  }

  .navbar-brand {
    flex: 1 1 auto;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .navbar-toggler {
    flex: 0 0 auto;
    /* ms-auto в разметке уже прижимает вправо, но страхуемся */
    margin-left: auto;
  }

  .navbar-nav.mx-auto {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .navbar-collapse {
    padding-top: 12px;
  }

  .main-nav-center {
    flex-direction: column;
    align-items: stretch !important;
    justify-content: flex-start !important;
    gap: 2px;
    width: 100%;
  }

  .main-nav-center .nav-item {
    width: 100%;
  }

  .top-link {
    width: 100%;
    display: flex;
    justify-content: flex-start;
  }

  .main-dropdown .dropdown-menu {
    position: static !important;
    float: none;
    transform: none !important;
    opacity: 0;
    max-height: 0;
    overflow: hidden;
    display: block;
    pointer-events: none;
    transition: all 0.25s ease;
    margin-top: 0px !important;
    padding: 0px;
  }

  .custom-menu .dropdown-item {
    padding: 0px 0px;
  }

  .main-dropdown .dropdown-menu.show {
    opacity: 1;
    max-height: 500px;
    pointer-events: auto;
  }

  .custom-menu {
    min-width: 100%;
  }

  .navbar .d-flex {
    width: 100%;
    justify-content: space-between;
    margin-top: 10px;
  }
}

/* layout */
.app-wrapper {
  min-height: 100vh;
  background: #f8f9fa;
}

.main-content {
  min-height: calc(100vh - 72px);
  padding-left: 258px !important;
  padding-right: 258px !important;
}

/* navbar */
.navbar-custom {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
}

.navbar-safe {
  padding-left: 28px;
  padding-right: 28px;
}

.brand-title {
  font-weight: 800;
  font-size: 20px;
  color: #111;
}

.brand-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
  border-radius: 8px;
}

/* center menu */
.main-nav-center {
  flex: 1;
  justify-content: center;
}

/* top links */
.top-link,
.user-link {
  font-size: 17px;
  font-weight: 700;
  color: #222 !important;
  border-radius: 14px;
  padding: 10px 16px !important;
  transition: all 0.22s ease;
}

.top-link:hover,
.user-link:hover {
  background: rgba(13, 110, 253, 0.08);
  color: #0d6efd !important;
}

.router-link-active.top-link {
  background: rgba(13, 110, 253, 0.12);
  color: #0d6efd !important;
}

/* dropdown */
.main-dropdown {
  position: relative;
}

.custom-menu {
  min-width: 290px;
  margin-top: 10px !important;
  padding: 10px;
  border-radius: 18px;

  opacity: 0;
  visibility: hidden;

  display: block;
  pointer-events: none;

  transition: opacity 0.18s ease, visibility 0.18s ease;
  z-index: 2000;
}

.navbar {
  z-index: 1050;
}

.dropdown-menu {
  z-index: 2000;
}

.main-dropdown .dropdown-menu.show {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

.custom-menu .dropdown-item {
  border-radius: 12px;
  padding: 11px 14px;
  font-weight: 600;
  transition: all 0.18s ease;
}

.custom-menu .dropdown-item:hover {
  background: #0d6efd;
  color: #fff;
  transform: translateX(4px);
}

.custom-menu .dropdown-item.router-link-active {
  background: rgba(13, 110, 253, 0.12);
  color: #0d6efd;
}

/* logout button */
.logout-btn {
  width: 44px;
  height: 44px;
  border: 0;
  background: transparent;
  border-radius: 14px;
  font-size: 22px;
  transition: all 0.2s ease;
}

.logout-btn:hover {
  background: rgba(220, 53, 69, 0.12);
  color: #dc3545;
  transform: scale(1.05);
}

/* modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}

.logout-card {
  width: 380px;
  max-width: calc(100vw - 24px);
  background: #fff;
  border-radius: 22px;
  padding: 28px;
  text-align: center;
}

.logout-icon {
  width: 62px;
  height: 62px;
  margin: 0 auto 16px;
  border-radius: 18px;
  background: rgba(220, 53, 69, 0.12);
  color: #dc3545;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.btn-cancel,
.btn-confirm {
  border: 0;
  border-radius: 14px;
  padding: 12px;
  font-weight: 700;
  transition: all 0.2s ease;
}

.btn-cancel {
  background: #eef1f4;
}

.btn-cancel:hover {
  background: #dde2e7;
}

.btn-confirm {
  background: #dc3545;
  color: #fff;
}

.btn-confirm:hover {
  background: #bb2d3b;
}

/* animation */
.fade-enter-active,
.fade-leave-active {
  transition: 0.22s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
</style>
