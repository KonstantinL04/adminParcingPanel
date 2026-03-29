<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";

const settings = ref([]);
const loading = ref(false);
const editing = ref(null);
const creating = ref(false);
const saving = ref(false);
const newSetting = ref({ key: "", value: "" });

async function fetchSettings() {
  loading.value = true;
  const r = await axios.get("/api/settings/");
  settings.value = r.data;
  loading.value = false;
}

function startEdit(s) {
  editing.value = { ...s };
}

function startCreate() {
  newSetting.value = { key: "", value: "" };
}

async function createSetting() {
  if (creating.value) return;
  if (!newSetting.value.key || !newSetting.value.value) {
    alert("Заполните key и value.");
    return;
  }
  creating.value = true;
  try {
    await axios.post("/api/settings/", {
      key: newSetting.value.key,
      value: newSetting.value.value,
    });
    const modalEl = document.getElementById("createSettingModal");
    if (modalEl) {
      const bsModal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
      bsModal.hide();
    }
    newSetting.value = { key: "", value: "" };
    await fetchSettings();
  } finally {
    creating.value = false;
  }
}

async function saveEdit() {
  if (!editing.value || saving.value) return;
  saving.value = true;
  try {
    await axios.put(`/api/settings/${editing.value.id}/`, {
      key: editing.value.key,
      value: editing.value.value,
    });
    editing.value = null;
    await fetchSettings();
  } finally {
    saving.value = false;
  }
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await fetchSettings();
});
</script>

<template>
  <div class="p-3">
    <div class="header-row">
      <h4>Настройки системы</h4>
      <button
        class="btn btn-success"
        data-bs-toggle="modal"
        data-bs-target="#createSettingModal"
        @click="startCreate"
      >
        <i class="bi bi-plus-lg"></i> Добавить
      </button>
    </div>

    <div v-if="loading">Загрузка...</div>

    <div v-else>
      <div v-for="s in settings" :key="s.id" class="setting-item">
        <div class="setting-info">
          <div class="setting-key">{{ s.key }}</div>
          <div class="setting-value text-muted">{{ s.value }}</div>
        </div>
        <div class="setting-actions">
          <button class="btn btn-warning" data-bs-toggle="modal" data-bs-target="#editSettingModal"
                  @click="startEdit(s)">
            <i class="bi bi-pen-fill"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <div class="modal fade" id="editSettingModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Изменить настройку</h5>
            <button class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body" v-if="editing">
            <div class="form-floating">
              <input type="text" class="form-control" v-model="editing.value" />
              <label>{{ editing.key }}</label>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
            <button class="btn btn-primary" data-bs-dismiss="modal" :disabled="saving" @click="saveEdit">
              <span v-if="saving" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
              Сохранить
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create modal -->
    <div class="modal fade" id="createSettingModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Добавить настройку</h5>
            <button class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="form-floating mb-3">
              <input type="text" class="form-control" v-model="newSetting.key" />
              <label>Key</label>
            </div>
            <div class="form-floating">
              <input type="text" class="form-control" v-model="newSetting.value" />
              <label>Value</label>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" data-bs-dismiss="modal" :disabled="creating">Отмена</button>
            <button class="btn btn-primary" :disabled="creating" @click="createSetting">
              <span v-if="creating" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
              Создать
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .5rem;
  margin: .5rem 0;
  border: 1px solid #ddd;
  border-radius: 8px;
}
.setting-info {
  display: flex;
  flex-direction: column;
}
.setting-key {
  font-weight: 600;
  font-size: 1.05rem;
}
.setting-value {
  font-size: .9rem;
}
.setting-actions {
  display: flex;
  gap: .5rem;
}
</style>
