<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";
// import { useUserStore } from "@/stores/user";

// const userStore = useUserStore();

const excludedUsers = ref([]);
const loading = ref(false);

const userToAdd = ref({ value: "" });
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
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await fetchExcludedUsers();
});
</script>

<template>
  <div class="p-3">
    <h4>Исключённые пользователи</h4>

    <!-- Добавление -->
    <form @submit.prevent.stop="onAddUser" class="mt-2">
      <div class="row g-2 align-items-center">
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="userToAdd.value" required />
            <label>Имя / ID пользователя</label>
          </div>
        </div>
        <div class="col-auto">
          <button class="btn btn-primary">Добавить</button>
        </div>
      </div>
    </form>

    <div v-if="loading" class="mt-3">Загрузка...</div>

    <!-- List -->
    <div v-else class="mt-3">
      <div v-for="u in excludedUsers" :key="u.id" class="item-box">
        <div class="item-text">{{ u.value }}</div>
        <div class="item-actions">
          <button class="btn btn-warning" data-bs-toggle="modal" data-bs-target="#editUserModal"
            @click="onEditUserClick(u)">
            <i class="bi bi-pen-fill"></i>
          </button>
          <button class="btn btn-danger" @click="onRemoveUser(u)">
            <i class="bi bi-trash3-fill"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <div class="modal fade" id="editUserModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Редактировать пользователя</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="form-floating">
              <input type="text" class="form-control" v-model="userToEdit.value" required />
              <label>Имя / ID пользователя</label>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
            <button class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateUserClick">
              Сохранить
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.item-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  margin-bottom: 0.5rem;
}

.item-text {
  font-size: 1rem;
  font-weight: 500;
}

.item-actions {
  display: flex;
  gap: 0.5rem;
}
</style>