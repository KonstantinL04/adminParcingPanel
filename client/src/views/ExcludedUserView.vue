<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";

const excludedUsers = ref([]);
const loading = ref(false);

const userToAdd = ref({
  value: "",
});

const userToEdit = ref({});

async function fetchExcludedUsers() {
  loading.value = true;

  const r = await axios.get("/api/excluded_users/");

  excludedUsers.value = r.data;

  loading.value = false;
}

async function onAddUser() {
  await axios.post("/api/excluded_users/", {
    value: userToAdd.value.value,
  });

  userToAdd.value.value = "";

  await fetchExcludedUsers();
}

async function onRemoveUser(user) {
  await axios.delete(`/api/excluded_users/${user.id}/`);

  await fetchExcludedUsers();
}

async function onEditUserClick(user) {
  userToEdit.value = { ...user };
}

async function onUpdateUserClick() {
  await axios.put(`/api/excluded_users/${userToEdit.value.id}/`, {
    value: userToEdit.value.value,
  });

  await fetchExcludedUsers();
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] =
    Cookies.get("csrftoken");

  await fetchExcludedUsers();
});
</script>

<template>
  <div class="page-wrap">

    <!-- HEADER -->

    <div class="page-header mb-4">

      <div>
        <h2 class="page-title">
          <i class="bi bi-person-x-fill me-2"></i>
          Исключённые пользователи
        </h2>

        <div class="page-subtitle">
          Пользователи, которых парсер игнорирует
        </div>
      </div>

    </div>

    <!-- ADD -->

    <div class="custom-card mb-4">

      <div class="card-title-custom">
        <i class="bi bi-plus-circle-fill me-2"></i>
        Добавить пользователя
      </div>

      <form @submit.prevent.stop="onAddUser">

        <div class="row g-3 align-items-end">

          <div class="col-lg">
            <label class="form-label">
              Имя / ID пользователя
            </label>

            <input
              type="text"
              class="form-control custom-input"
              v-model="userToAdd.value"
              required
              placeholder="@username или ID"
            />
          </div>

          <div class="col-lg-auto">
            <button class="btn-create">
              <i class="bi bi-plus-lg me-2"></i>
              Добавить
            </button>
          </div>

        </div>

      </form>

    </div>

    <!-- LIST -->

    <div class="custom-card">

      <div class="card-title-custom mb-4">
        <i class="bi bi-list-ul me-2"></i>
        Список пользователей
      </div>

      <div
        v-if="loading"
        class="loading-box"
      >
        Загрузка...
      </div>

      <div
        v-else-if="excludedUsers.length === 0"
        class="empty-box"
      >
        <i class="bi bi-inbox me-2"></i>
        Список пуст
      </div>

      <div
        v-else
        class="users-grid"
      >

        <div
          v-for="u in excludedUsers"
          :key="u.id"
          class="user-card"
        >

          <div class="user-left">

            <div class="user-avatar">
              <i class="bi bi-person-fill"></i>
            </div>

            <div>
              <div class="user-name">
                {{ u.value }}
              </div>

              <div class="user-id">
                ID: {{ u.id }}
              </div>
            </div>

          </div>

          <div class="item-actions">

            <button
              class="btn-action btn-edit"
              data-bs-toggle="modal"
              data-bs-target="#editUserModal"
              @click="onEditUserClick(u)"
            >
              <i class="bi bi-pencil-square me-1"></i>
              Редактировать
            </button>

            <button
              class="btn-action btn-delete"
              @click="onRemoveUser(u)"
            >
              <i class="bi bi-trash3 me-1"></i>
              Удалить
            </button>

          </div>

        </div>

      </div>

    </div>

    <!-- MODAL -->

    <div
      class="modal fade"
      id="editUserModal"
      tabindex="-1"
    >

      <div class="modal-dialog modal-dialog-centered">

        <div class="modal-content custom-modal">

          <div class="modal-header border-0 pb-0">

            <h5 class="modal-title fw-bold">
              Редактировать пользователя
            </h5>

            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
            ></button>

          </div>

          <div class="modal-body">

            <label class="form-label">
              Имя / ID пользователя
            </label>

            <input
              type="text"
              class="form-control custom-input"
              v-model="userToEdit.value"
              required
            />

          </div>

          <div class="modal-footer border-0 pt-0">

            <button
              class="btn-cancel"
              data-bs-dismiss="modal"
            >
              Отмена
            </button>

            <button
              class="btn-save"
              data-bs-dismiss="modal"
              @click="onUpdateUserClick"
            >
              Сохранить
            </button>

          </div>

        </div>

      </div>

    </div>

  </div>
</template>

<style scoped>
.page-wrap {
  padding: 8px 0 30px;
}

.page-title {
  font-size: 28px;
  font-weight: 800;
  color: #111;
  margin-bottom: 4px;
}

.page-subtitle {
  color: #6c757d;
  font-size: 15px;
}

.custom-card {
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(15,23,42,0.06);
  border: 1px solid rgba(0,0,0,0.04);
}

.card-title-custom {
  font-size: 18px;
  font-weight: 800;
  margin-bottom: 18px;
  color: #111;
}

.custom-input {
  border-radius: 14px;
  border: 1px solid #dfe3e8;
  padding: 12px 14px;
  font-weight: 500;
  box-shadow: none !important;
}

.custom-input:focus {
  border-color: #0d6efd;
}

.btn-create {
  border: 0;
  background: #0d6efd;
  color: #fff;
  padding: 12px 20px;
  border-radius: 14px;
  font-weight: 700;
  transition: 0.2s ease;
}

.btn-create:hover {
  background: #0b5ed7;
  transform: translateY(-1px);
}

.users-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.user-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 18px;
  border-radius: 20px;
  background: #f8fafc;
  border: 1px solid #eef1f4;
  transition: 0.2s ease;
}

.user-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15,23,42,0.06);
}

.user-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-avatar {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: rgba(13,110,253,0.1);
  color: #0d6efd;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.user-name {
  font-size: 16px;
  font-weight: 700;
  color: #111;
}

.user-id {
  font-size: 13px;
  color: #6c757d;
  margin-top: 2px;
}

.item-actions {
  display: flex;
  gap: 10px;
}

.btn-action {
  border: 0;
  border-radius: 14px;
  padding: 10px 14px;
  font-weight: 700;
  transition: 0.2s ease;
}

.btn-edit {
  background: rgba(13,110,253,0.1);
  color: #0d6efd;
}

.btn-edit:hover {
  background: #0d6efd;
  color: #fff;
}

.btn-delete {
  background: rgba(220,53,69,0.1);
  color: #dc3545;
}

.btn-delete:hover {
  background: #dc3545;
  color: #fff;
}

.loading-box,
.empty-box {
  padding: 40px;
  text-align: center;
  color: #6c757d;
  font-weight: 600;
}

.custom-modal {
  border: 0;
  border-radius: 24px;
  padding: 10px;
}

.btn-cancel,
.btn-save {
  border: 0;
  border-radius: 14px;
  padding: 12px 20px;
  font-weight: 700;
}

.btn-cancel {
  background: #eef1f4;
}

.btn-save {
  background: #0d6efd;
  color: #fff;
}

@media (max-width: 991.98px) {

  .custom-card {
    padding: 18px;
    border-radius: 20px;
  }

  .page-title {
    font-size: 22px;
  }

  .user-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .item-actions {
    width: 100%;
    flex-direction: column;
  }

  .btn-action,
  .btn-create {
    width: 100%;
  }
}
</style>