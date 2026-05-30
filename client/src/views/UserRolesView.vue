<script setup>
import { computed, onMounted, ref } from "vue";
import axios from "axios";

const loading = ref(false);
const saving = ref(false);
const error = ref("");
const success = ref("");

const users = ref([]);
const roles = ref([]);
const userRoles = ref([]);
const form = ref({ user: "", role: "" });

const enrichedRows = computed(() => {
  const userMap = new Map(users.value.map((u) => [u.id, u]));
  const roleMap = new Map(roles.value.map((r) => [r.id, r]));
  return userRoles.value.map((row) => ({
    ...row,
    user_email: userMap.get(row.user)?.email || `#${row.user}`,
    user_name: userMap.get(row.user)?.username || "",
    role_name: roleMap.get(row.role)?.name || `#${row.role}`,
  })).sort((a, b) => a.user_email.localeCompare(b.user_email));
});

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    const [usersRes, rolesRes, rowsRes] = await Promise.all([
      axios.get("/api/accounts/users/"),
      axios.get("/api/accounts/roles/"),
      axios.get("/api/accounts/user_roles/"),
    ]);
    users.value = Array.isArray(usersRes.data?.results) ? usersRes.data.results : Array.isArray(usersRes.data) ? usersRes.data : [];
    roles.value = Array.isArray(rolesRes.data?.results) ? rolesRes.data.results : Array.isArray(rolesRes.data) ? rolesRes.data : [];
    userRoles.value = Array.isArray(rowsRes.data?.results) ? rowsRes.data.results : Array.isArray(rowsRes.data) ? rowsRes.data : [];
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось загрузить роли пользователей";
  } finally {
    loading.value = false;
  }
}

async function addRoleBinding() {
  if (!form.value.user || !form.value.role) return;
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.post("/api/accounts/user_roles/", {
      user: Number(form.value.user),
      role: Number(form.value.role),
    });
    form.value = { user: "", role: "" };
    success.value = "Роль назначена";
    await loadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось назначить роль";
  } finally {
    saving.value = false;
  }
}

async function removeBinding(id) {
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.delete(`/api/accounts/user_roles/${id}/`);
    success.value = "Назначение удалено";
    await loadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось удалить назначение";
  } finally {
    saving.value = false;
  }
}

onMounted(loadAll);
</script>

<template>
  <div class="page-wrap">
    <div class="page-header mb-4">
      <div>
        <h2 class="page-title">
          <i class="bi bi-person-gear me-2"></i>
          Назначение ролей
        </h2>
        <div class="page-subtitle">Управление правами доступа пользователей</div>
      </div>
      <button class="btn-refresh" :disabled="loading" @click="loadAll">
        <i class="bi bi-arrow-clockwise"></i>
      </button>
    </div>

    <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
    <div v-if="success" class="alert alert-success py-2">{{ success }}</div>

    <div class="custom-card mb-4">
      <div class="card-title-custom">
        <i class="bi bi-plus-circle-fill me-2"></i>
        Назначить роль
      </div>

      <div class="row g-3 align-items-end">
        <div class="col-xl-5 col-lg-6">
          <label class="form-label">Пользователь</label>
          <select class="form-select custom-input" v-model="form.user">
            <option value="">Выберите пользователя</option>
            <option v-for="u in users" :key="u.id" :value="u.id">
              {{ u.email }} · ID {{ u.id }}
            </option>
          </select>
        </div>
        <div class="col-xl-4 col-lg-6">
          <label class="form-label">Роль</label>
          <select class="form-select custom-input" v-model="form.role">
            <option value="">Выберите роль</option>
            <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </div>
        <div class="col-xl-3 d-grid">
          <button class="btn-create" :disabled="saving" @click="addRoleBinding">
            <i class="bi bi-plus-lg me-2"></i>
            Назначить
          </button>
        </div>
      </div>
    </div>

    <div class="custom-card">
      <div class="card-title-custom mb-4">
        <i class="bi bi-list-ul me-2"></i>
        Текущие роли
      </div>

      <div v-if="loading" class="loading-box">Загрузка...</div>
      <div v-else-if="enrichedRows.length === 0" class="empty-box">
        <i class="bi bi-inbox me-2"></i>
        Назначений пока нет
      </div>
      <div v-else class="roles-grid">
        <div v-for="row in enrichedRows" :key="row.id" class="role-card">
          <div class="role-left">
            <div class="role-icon">
              <i class="bi bi-person-badge-fill"></i>
            </div>
            <div class="min-w-0">
              <div class="role-user">{{ row.user_email }}</div>
              <div class="role-meta">ID {{ row.user }} · {{ row.user_name || "без username" }}</div>
            </div>
          </div>
          <span class="role-pill">{{ row.role_name }}</span>
          <button class="btn-action btn-delete" :disabled="saving" @click="removeBinding(row.id)">
            <i class="bi bi-trash3 me-1"></i>
            Удалить
          </button>
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
.btn-create,
.btn-refresh,
.btn-action {
  border: 0;
  font-weight: 800;
}
.btn-create {
  border-radius: 14px;
  padding: 12px 22px;
  background: #0d6efd;
  color: #fff;
}
.btn-refresh {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: #edf4ff;
  color: #0d6efd;
}
.roles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 14px;
}
.role-card {
  border: 1px solid #edf0f4;
  border-radius: 18px;
  padding: 16px;
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 12px;
  align-items: center;
}
.role-left {
  display: flex;
  gap: 12px;
  min-width: 0;
}
.role-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: #eef5ff;
  color: #0d6efd;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
}
.role-user {
  font-weight: 800;
  overflow-wrap: anywhere;
}
.role-meta {
  color: #7b8190;
  font-size: 13px;
}
.role-pill {
  border-radius: 999px;
  background: #f1f5f9;
  color: #334155;
  padding: 6px 10px;
  font-weight: 800;
}
.btn-delete {
  background: #fff1f1;
  color: #dc3545;
  border-radius: 12px;
  padding: 10px 12px;
}
.loading-box,
.empty-box {
  border-radius: 18px;
  background: #f8fafc;
  padding: 28px;
  text-align: center;
  color: #7b8190;
}
@media (max-width: 768px) {
  .role-card {
    grid-template-columns: 1fr;
  }
}
</style>
