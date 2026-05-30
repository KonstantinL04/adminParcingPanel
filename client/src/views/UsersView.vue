<script setup>
import { computed, onMounted, ref } from "vue";
import axios from "axios";

const loading = ref(false);
const saving = ref(false);
const error = ref("");
const success = ref("");
const users = ref([]);

const form = ref({
  email: "",
  username: "",
  password: "",
  is_active: true,
  is_staff: false,
  is_superuser: false,
});
const editForm = ref({});
const reputationLogs = ref([]);
const selectedUser = ref(null);
const logsLoading = ref(false);

const sortedUsers = computed(() =>
  [...users.value].sort((a, b) => Number(a.id) - Number(b.id))
);

function formatDate(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

function resetForm() {
  form.value = {
    email: "",
    username: "",
    password: "",
    is_active: true,
    is_staff: false,
    is_superuser: false,
  };
}

async function loadUsers() {
  loading.value = true;
  error.value = "";
  try {
    const { data } = await axios.get("/api/accounts/users/");
    users.value = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось загрузить пользователей";
  } finally {
    loading.value = false;
  }
}

async function createUser() {
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.post("/api/accounts/users/", {
      email: form.value.email,
      username: form.value.username || null,
      password: form.value.password,
      is_active: form.value.is_active,
      is_staff: form.value.is_staff,
      is_superuser: form.value.is_superuser,
    });
    resetForm();
    success.value = "Пользователь добавлен";
    await loadUsers();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось добавить пользователя";
  } finally {
    saving.value = false;
  }
}

function openEdit(user) {
  editForm.value = {
    ...user,
    password: "",
    username: user.username || "",
  };
}

async function updateUser() {
  if (!editForm.value.id) return;
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    const payload = {
      email: editForm.value.email,
      username: editForm.value.username || null,
      is_active: editForm.value.is_active,
      is_staff: editForm.value.is_staff,
      is_superuser: editForm.value.is_superuser,
    };
    if (editForm.value.password) payload.password = editForm.value.password;
    await axios.patch(`/api/accounts/users/${editForm.value.id}/`, payload);
    success.value = "Пользователь обновлен";
    await loadUsers();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось обновить пользователя";
  } finally {
    saving.value = false;
  }
}

async function deleteUser(user) {
  if (!window.confirm(`Удалить пользователя ${user.email}?`)) return;
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.delete(`/api/accounts/users/${user.id}/`);
    success.value = "Пользователь удален";
    await loadUsers();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось удалить пользователя";
  } finally {
    saving.value = false;
  }
}

async function openReputation(user) {
  selectedUser.value = user;
  logsLoading.value = true;
  reputationLogs.value = [];
  try {
    const { data } = await axios.get("/api/accounts/reputation/", {
      params: { user: user.id },
    });
    reputationLogs.value = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось загрузить историю рейтинга";
  } finally {
    logsLoading.value = false;
  }
}

onMounted(loadUsers);
</script>

<template>
  <div class="page-wrap">
    <div class="page-header mb-4">
      <div>
        <h2 class="page-title">
          <i class="bi bi-people-fill me-2"></i>
          Пользователи
        </h2>
        <div class="page-subtitle">Учетные записи, доступы и статус пользователей</div>
      </div>
      <button class="btn-refresh" :disabled="loading" @click="loadUsers">
        <i class="bi bi-arrow-clockwise"></i>
      </button>
    </div>

    <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
    <div v-if="success" class="alert alert-success py-2">{{ success }}</div>

    <div class="custom-card mb-4">
      <div class="card-title-custom">
        <i class="bi bi-person-plus-fill me-2"></i>
        Добавить пользователя
      </div>

      <form @submit.prevent="createUser">
        <div class="row g-3 align-items-end">
          <div class="col-xl-3 col-lg-6">
            <label class="form-label">Email</label>
            <input class="form-control custom-input" type="email" v-model="form.email" required />
          </div>
          <div class="col-xl-3 col-lg-6">
            <label class="form-label">Username</label>
            <input class="form-control custom-input" v-model="form.username" />
          </div>
          <div class="col-xl-3 col-lg-6">
            <label class="form-label">Пароль</label>
            <input class="form-control custom-input" type="password" v-model="form.password" required />
          </div>
          <div class="col-xl-3 col-lg-6 flags-row">
            <label class="flag-item"><input type="checkbox" v-model="form.is_active" /> Активен</label>
            <label class="flag-item"><input type="checkbox" v-model="form.is_staff" /> Staff</label>
            <label class="flag-item"><input type="checkbox" v-model="form.is_superuser" /> Admin</label>
          </div>
          <div class="col-12 d-flex justify-content-end">
            <button class="btn-create" :disabled="saving">
              <i class="bi bi-plus-lg me-2"></i>
              Добавить
            </button>
          </div>
        </div>
      </form>
    </div>

    <div class="custom-card">
      <div class="card-title-custom mb-4">
        <i class="bi bi-list-ul me-2"></i>
        Список пользователей
      </div>

      <div v-if="loading" class="loading-box">Загрузка...</div>
      <div v-else-if="sortedUsers.length === 0" class="empty-box">
        <i class="bi bi-inbox me-2"></i>
        Пользователей нет
      </div>
      <div v-else class="user-grid">
        <div v-for="u in sortedUsers" :key="u.id" class="user-card">
          <div class="user-main">
            <div class="avatar"><i class="bi bi-person-fill"></i></div>
            <div class="min-w-0">
              <div class="user-email">{{ u.email }}</div>
              <div class="user-meta">ID {{ u.id }} · {{ u.username || "без username" }}</div>
              <div class="role-line">
                <span v-for="r in (u.roles || [])" :key="r" class="role-pill">{{ r }}</span>
                <span v-if="!u.roles?.length" class="text-muted small">ролей нет</span>
              </div>
            </div>
          </div>
          <div class="status-wrap">
            <span class="badge" :class="u.is_active ? 'text-bg-success' : 'text-bg-secondary'">
              {{ u.is_active ? "Активен" : "Отключен" }}
            </span>
            <span v-if="u.is_staff" class="badge text-bg-primary">staff</span>
            <span v-if="u.is_superuser" class="badge text-bg-danger">admin</span>
            <button class="reputation-pill" data-bs-toggle="modal" data-bs-target="#reputationModal" @click="openReputation(u)">
              <i class="bi bi-star-fill me-1"></i>
              {{ u.reputation ?? 0 }}
            </button>
          </div>
          <div class="user-dates">
            <span>Регистрация: {{ formatDate(u.date_joined) }}</span>
            <span>Вход: {{ formatDate(u.last_login) }}</span>
          </div>
          <div class="item-actions">
            <button class="btn-action btn-edit" data-bs-toggle="modal" data-bs-target="#editUserModal" @click="openEdit(u)">
              <i class="bi bi-pencil-square me-1"></i>
              Редактировать
            </button>
            <button class="btn-action btn-delete" :disabled="saving" @click="deleteUser(u)">
              <i class="bi bi-trash3 me-1"></i>
              Удалить
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" id="editUserModal" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content custom-modal">
          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title fw-bold">Редактировать пользователя</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label">Email</label>
                <input class="form-control custom-input" type="email" v-model="editForm.email" />
              </div>
              <div class="col-12">
                <label class="form-label">Username</label>
                <input class="form-control custom-input" v-model="editForm.username" />
              </div>
              <div class="col-12">
                <label class="form-label">Новый пароль</label>
                <input class="form-control custom-input" type="password" v-model="editForm.password" placeholder="Оставьте пустым, если не менять" />
              </div>
              <div class="col-12 flags-row">
                <label class="flag-item"><input type="checkbox" v-model="editForm.is_active" /> Активен</label>
                <label class="flag-item"><input type="checkbox" v-model="editForm.is_staff" /> Staff</label>
                <label class="flag-item"><input type="checkbox" v-model="editForm.is_superuser" /> Admin</label>
              </div>
            </div>
          </div>
          <div class="modal-footer border-0">
            <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
            <button class="btn btn-primary" :disabled="saving" @click="updateUser">Сохранить</button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" id="reputationModal" tabindex="-1">
      <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content custom-modal">
          <div class="modal-header border-0 pb-0">
            <div>
              <h5 class="modal-title fw-bold">Рейтинг пользователя</h5>
              <div class="text-muted small">{{ selectedUser?.email }}</div>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="reputation-summary">
              <div>
                <div class="text-muted small">Текущий рейтинг</div>
                <div class="reputation-score">{{ selectedUser?.reputation ?? 0 }}</div>
              </div>
            </div>

            <div v-if="logsLoading" class="loading-box mt-3">Загрузка истории...</div>
            <div v-else-if="reputationLogs.length === 0" class="empty-box mt-3">Истории рейтинга пока нет</div>
            <div v-else class="reputation-list mt-3">
              <div v-for="log in reputationLogs" :key="log.id" class="reputation-log">
                <div>
                  <div class="fw-bold">{{ log.action }}</div>
                  <div class="text-muted small">{{ log.comment || "Без комментария" }}</div>
                  <div class="text-muted small">{{ formatDate(log.created_at) }}</div>
                </div>
                <div class="reputation-delta" :class="{ positive: log.reputation_delta > 0, negative: log.reputation_delta < 0 }">
                  {{ log.reputation_delta > 0 ? "+" : "" }}{{ log.reputation_delta }}
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer border-0">
            <button class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-wrap {
  padding: 24px;
}
.page-header {
  background: #fff;
  border-radius: 24px;
  padding: 22px 26px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.page-title {
  font-weight: 800;
  margin: 0;
  color: #1f2937;
}
.page-subtitle {
  color: #7b8190;
  margin-top: 4px;
}
.custom-card {
  background: #fff;
  border-radius: 24px;
  padding: 22px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
}
.card-title-custom {
  font-weight: 800;
  font-size: 18px;
  margin-bottom: 18px;
}
.custom-input {
  border-radius: 14px;
  border: 1px solid #d9dee8;
  min-height: 44px;
}
.btn-create {
  border: 0;
  border-radius: 14px;
  padding: 12px 22px;
  background: #0d6efd;
  color: #fff;
  font-weight: 800;
}
.btn-refresh {
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 14px;
  background: #edf4ff;
  color: #0d6efd;
}
.flags-row {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  align-items: center;
}
.flag-item {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  font-weight: 700;
}
.user-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 14px;
}
.user-card {
  border: 1px solid #edf0f4;
  border-radius: 18px;
  padding: 16px;
}
.user-main {
  display: flex;
  gap: 12px;
  min-width: 0;
}
.avatar {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: #eef5ff;
  color: #0d6efd;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
}
.user-email {
  font-weight: 800;
  overflow-wrap: anywhere;
}
.user-meta,
.user-dates {
  color: #7b8190;
  font-size: 13px;
}
.role-line,
.status-wrap,
.item-actions,
.user-dates {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.role-pill {
  background: #f1f5f9;
  color: #334155;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 700;
}
.reputation-pill {
  border: 0;
  border-radius: 999px;
  padding: 4px 10px;
  color: #915d00;
  background: #fff4d6;
  font-size: 12px;
  font-weight: 900;
}
.btn-action {
  border: 0;
  border-radius: 12px;
  padding: 8px 12px;
  font-weight: 800;
}
.btn-edit {
  background: #eef5ff;
  color: #0d6efd;
}
.btn-delete {
  background: #fff1f1;
  color: #dc3545;
}
.loading-box,
.empty-box {
  border-radius: 18px;
  background: #f8fafc;
  padding: 28px;
  text-align: center;
  color: #7b8190;
}
.custom-modal {
  border: 0;
  border-radius: 22px;
}
.reputation-summary {
  padding: 16px;
  border-radius: 18px;
  background: #f8fafc;
}
.reputation-score {
  color: #111827;
  font-size: 34px;
  font-weight: 900;
}
.reputation-list {
  display: grid;
  gap: 10px;
}
.reputation-log {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border: 1px solid #edf0f4;
  border-radius: 16px;
}
.reputation-delta {
  min-width: 48px;
  text-align: right;
  color: #64748b;
  font-size: 20px;
  font-weight: 900;
}
.reputation-delta.positive {
  color: #087443;
}
.reputation-delta.negative {
  color: #b42318;
}
</style>
