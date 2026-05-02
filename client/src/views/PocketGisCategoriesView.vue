<script setup>
import { onMounted, ref } from "vue";
import axios from "axios";

const categories = ref([]);
const isLoading = ref(false);
const isSaving = ref(false);
const message = ref("");
const error = ref("");

const newCategory = ref({
  type_code: "",
  name: "",
  enabled: true,
  sort_order: 0,
  icon: null,
});

function toAbsoluteMedia(url) {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${window.location.origin}${url}`;
}

function onNewIconChange(event) {
  newCategory.value.icon = event.target.files?.[0] || null;
}

function onRowIconChange(row, event) {
  row._iconFile = event.target.files?.[0] || null;
}

async function loadCategories() {
  isLoading.value = true;
  try {
    const { data } = await axios.get("/api/events/pocketgis/categories/");
    categories.value = (Array.isArray(data) ? data : []).map((row) => ({
      ...row,
      _iconFile: null,
      _saving: false,
    }));
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось загрузить категории.";
  } finally {
    isLoading.value = false;
  }
}

async function createCategory() {
  if (!newCategory.value.type_code || !newCategory.value.name.trim()) {
    error.value = "Заполните код и название категории.";
    return;
  }

  isSaving.value = true;
  message.value = "";
  error.value = "";

  try {
    const fd = new FormData();
    fd.append("type_code", String(newCategory.value.type_code));
    fd.append("name", newCategory.value.name.trim());
    fd.append("enabled", String(Boolean(newCategory.value.enabled)));
    fd.append("sort_order", String(Number(newCategory.value.sort_order || 0)));
    if (newCategory.value.icon) fd.append("icon", newCategory.value.icon);

    await axios.post("/api/events/pocketgis/categories/", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    message.value = "Категория создана.";
    newCategory.value = { type_code: "", name: "", enabled: true, sort_order: 0, icon: null };
    const input = document.getElementById("new-pocketgis-icon-input");
    if (input) input.value = "";
    await loadCategories();
  } catch (e) {
    error.value = e?.response?.data?.detail || JSON.stringify(e?.response?.data || {}) || "Ошибка создания категории.";
  } finally {
    isSaving.value = false;
  }
}

async function saveRow(row) {
  row._saving = true;
  message.value = "";
  error.value = "";

  try {
    const fd = new FormData();
    fd.append("type_code", String(row.type_code));
    fd.append("name", row.name);
    fd.append("enabled", String(Boolean(row.enabled)));
    fd.append("sort_order", String(Number(row.sort_order || 0)));
    if (row._iconFile) fd.append("icon", row._iconFile);

    await axios.patch(`/api/events/pocketgis/categories/${row.id}/`, fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    message.value = `Категория «${row.name}» обновлена.`;
    await loadCategories();
  } catch (e) {
    error.value = e?.response?.data?.detail || JSON.stringify(e?.response?.data || {}) || "Ошибка обновления категории.";
  } finally {
    row._saving = false;
  }
}

onMounted(loadCategories);
</script>

<template>
  <div class="container-fluid p-3">
    <h4 class="mb-3">Категории PocketGis</h4>

    <div class="card mb-3">
      <div class="card-header fw-semibold">Добавить категорию</div>
      <div class="card-body">
        <div class="row g-3 align-items-end">
          <div class="col-md-2">
            <label class="form-label">Код типа</label>
            <input class="form-control" type="number" v-model.number="newCategory.type_code" />
          </div>
          <div class="col-md-3">
            <label class="form-label">Название</label>
            <input class="form-control" type="text" v-model="newCategory.name" />
          </div>
          <div class="col-md-2">
            <label class="form-label">Порядок</label>
            <input class="form-control" type="number" v-model.number="newCategory.sort_order" />
          </div>
          <div class="col-md-2">
            <label class="form-label">Иконка</label>
            <input id="new-pocketgis-icon-input" class="form-control" type="file" accept="image/*" @change="onNewIconChange" />
          </div>
          <div class="col-md-1 form-check mt-4">
            <input class="form-check-input" type="checkbox" id="new-enabled" v-model="newCategory.enabled" />
            <label class="form-check-label" for="new-enabled">Активна</label>
          </div>
          <div class="col-md-2 d-grid">
            <button class="btn btn-primary" :disabled="isSaving" @click="createCategory">
              <span v-if="isSaving" class="spinner-border spinner-border-sm me-2"></span>
              Создать
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="alert alert-success" v-if="message">{{ message }}</div>
    <div class="alert alert-danger" v-if="error">{{ error }}</div>

    <div class="card">
      <div class="card-header fw-semibold">Список категорий</div>
      <div class="table-responsive table-wrap">
        <table class="table table-sm table-striped align-middle mb-0">
          <thead class="table-light sticky-top">
            <tr>
              <th>ID</th>
              <th>Код</th>
              <th>Название</th>
              <th>Иконка</th>
              <th>Новая иконка</th>
              <th>Порядок</th>
              <th>Активна</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isLoading">
              <td colspan="8" class="text-center py-3">Загрузка...</td>
            </tr>
            <tr v-for="row in categories" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.type_code }}</td>
              <td>
                <input class="form-control form-control-sm" v-model="row.name" />
              </td>
              <td>
                <img v-if="row.icon" :src="toAbsoluteMedia(row.icon)" alt="icon" class="cat-icon" />
                <span v-else class="text-muted">—</span>
              </td>
              <td>
                <input class="form-control form-control-sm" type="file" accept="image/*" @change="(e) => onRowIconChange(row, e)" />
              </td>
              <td>
                <input class="form-control form-control-sm" type="number" v-model.number="row.sort_order" />
              </td>
              <td>
                <input class="form-check-input" type="checkbox" v-model="row.enabled" />
              </td>
              <td>
                <button class="btn btn-sm btn-outline-primary" :disabled="row._saving" @click="saveRow(row)">
                  <span v-if="row._saving" class="spinner-border spinner-border-sm me-1"></span>
                  Сохранить
                </button>
              </td>
            </tr>
            <tr v-if="!isLoading && categories.length === 0">
              <td colspan="8" class="text-center py-3 text-muted">Категорий пока нет</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.table-wrap {
  max-height: 70vh;
}

.cat-icon {
  width: 32px;
  height: 32px;
  object-fit: contain;
}
</style>
