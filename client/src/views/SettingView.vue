<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";

const settings = ref([]);
const loading = ref(false);
const editing = ref(null);

async function fetchSettings() {
  loading.value = true;
  const r = await axios.get("/api/settings/");
  settings.value = r.data;
  loading.value = false;
}

function startEdit(s) {
  editing.value = { ...s };
}

async function saveEdit() {
  await axios.put(`/api/settings/${editing.value.id}/`, {
    key: editing.value.key,
    value: editing.value.value,
  });
  editing.value = null;
  await fetchSettings();
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await fetchSettings();
});
</script>

<template>
  <div class="p-3">
    <h4>Настройки системы</h4>

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
            <button class="btn btn-primary" data-bs-dismiss="modal" @click="saveEdit">Сохранить</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
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