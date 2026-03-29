<script setup>
import axios from "axios";
import { ref, onBeforeMount, computed } from "vue";
import Cookies from "js-cookie";

const settings = ref([]);
const editing = ref({ key: "", value: "" });
const loading = ref(false);
const saving = ref(false);
const creating = ref(false);
const newSetting = ref({ key: "", value: "" });
const hasEditing = computed(() => !!editing.value.key);

async function fetchSettings() {
  loading.value = true;
  try {
    const r = await axios.get("/api/settings_api/");
    settings.value = r.data;
  } finally {
    loading.value = false;
  }
}

function startEdit(s) {
  editing.value = { key: s.key, value: "" };
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
    const payload = {
      key: newSetting.value.key,
      value: newSetting.value.value,
    };

    const resp = await axios.post("/api/settings_api/", payload);
    const created = resp.data || payload;
    const exists = settings.value.findIndex(s => s.key === created.key);
    if (exists === -1) {
      settings.value.push(created);
    }

    const modalEl = document.getElementById("createApiSettingModal");
    if (modalEl && window.bootstrap?.Modal) {
      const bsModal = window.bootstrap.Modal.getInstance(modalEl) || new window.bootstrap.Modal(modalEl);
      bsModal.hide();
    }

    newSetting.value = { key: "", value: "" };
  } catch (e) {
    console.error("Ошибка при создании API setting:", e);
    alert("Ошибка при создании. Смотри консоль.");
  } finally {
    creating.value = false;
  }
}

async function saveEdit() {
  if (!editing.value || saving.value) return;
  saving.value = true;

  try {
    const payload = {
      key: editing.value.key,
      value: editing.value.value,
    };

    const resp = await axios.put(`/api/settings_api/${encodeURIComponent(editing.value.key)}/`, payload);
    const updated = resp.data || { key: editing.value.key, value: "<updated>" };

    const idx = settings.value.findIndex(s => s.key === updated.key);
    if (idx !== -1) {
      settings.value[idx] = { ...settings.value[idx], ...updated };
    } else {
      settings.value.push(updated);
    }

    const modalEl = document.getElementById("editApiSettingModal");
    if (modalEl && window.bootstrap?.Modal) {
      const bsModal = window.bootstrap.Modal.getInstance(modalEl) || new window.bootstrap.Modal(modalEl);
      bsModal.hide();
    }

    editing.value = { key: "", value: "" };
  } catch (e) {
    console.error("Ошибка при сохранении API setting:", e);
    alert("Ошибка при сохранении. Смотри консоль.");
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
      <div>
        <h4>Настройки API Telegram</h4>
        <p class="text-muted">Хранятся в зашифрованном виде. Старые значения не показываются.</p>
      </div>
      <button
        class="btn btn-success"
        data-bs-toggle="modal"
        data-bs-target="#createApiSettingModal"
        @click="startCreate"
      >
        <i class="bi bi-plus-lg"></i> Добавить
      </button>
    </div>

    <div v-if="loading">Загрузка...</div>

    <div v-else>
      <div v-for="s in settings" :key="s.key" class="setting-item">
        <div class="setting-info">
          <div class="setting-key">{{ s.key }}</div>
          <div class="setting-value text-muted">{{ s.value }}</div>
        </div>
        <div class="setting-actions">
          <button class="btn btn-warning btn-sm" 
                  data-bs-toggle="modal" 
                  data-bs-target="#editApiSettingModal"
                  @click="startEdit(s)">
            <i class="bi bi-pen-fill"></i> 
          </button>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <div class="modal fade" id="editApiSettingModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">

          <div class="modal-header">
            <h5 class="modal-title">Обновить секретный ключ</h5>
            <button class="btn-close" data-bs-dismiss="modal"></button>
          </div>

          <div class="modal-body">
            <div v-if="hasEditing">
              <div class="form-floating">
                <input type="text" v-model="editing.value" class="form-control" />
                <label>Новое значение (старое не показывается)</label>
              </div>
            </div>
            <div v-else class="text-muted">Выберите ключ для редактирования</div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" data-bs-dismiss="modal" :disabled="saving">Отмена</button>
            <button class="btn btn-primary" :disabled="saving || !hasEditing" @click="saveEdit">
              <span v-if="saving" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
              Сохранить
            </button>
          </div>

        </div>
      </div>
    </div>

    <!-- Create modal -->
    <div class="modal fade" id="createApiSettingModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">

          <div class="modal-header">
            <h5 class="modal-title">Добавить новый ключ</h5>
            <button class="btn-close" data-bs-dismiss="modal"></button>
          </div>

          <div class="modal-body">
            <div class="form-floating mb-3">
              <input type="text" v-model="newSetting.key" class="form-control" />
              <label>Key</label>
            </div>
            <div class="form-floating">
              <input type="text" v-model="newSetting.value" class="form-control" />
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
