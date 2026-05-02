<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";

const categories = ref([]);
const loading = ref(false);

const categoryToAdd = ref({
  name: "",
  text_patterns: "",
  emoji_patterns: "",
  ttl_minutes: 60,
  confirm_threshold: 3,
  deny_threshold: -3,
  enabled: true,
});
const categoryImageToAdd = ref(null);
const addImagePreview = ref("");

const categoryToEdit = ref({});
const categoryImageToEdit = ref(null);
const editImagePreview = ref("");

function parsePatterns(str) {
  return str
    .split(",")
    .map(s => s.trim())
    .filter(s => s.length > 0);
}

function joinPatterns(arr) {
  return arr.join(", ");
}

function resolveImageUrl(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return path.startsWith("/") ? path : `/${path}`;
}

function buildCategoryFormData(source, imageFile) {
  const fd = new FormData();
  fd.append("name", source.name);
  fd.append("text_patterns", JSON.stringify(parsePatterns(source.text_patterns)));
  fd.append("emoji_patterns", JSON.stringify(parsePatterns(source.emoji_patterns)));
  fd.append("ttl_minutes", String(Number(source.ttl_minutes)));
  fd.append("confirm_threshold", String(Number(source.confirm_threshold)));
  fd.append("deny_threshold", String(Number(source.deny_threshold)));
  fd.append("enabled", source.enabled ? "true" : "false");
  if (imageFile) {
    fd.append("image", imageFile);
  }
  return fd;
}

async function fetchCategories() {
  loading.value = true;
  const r = await axios.get("/api/alert_categories/");
  categories.value = r.data.map(cat => ({
    ...cat,
    enabled: !!cat.enabled 
  }));
  loading.value = false;
}
async function onAddCategory() {
  const formData = buildCategoryFormData(categoryToAdd.value, categoryImageToAdd.value);
  await axios.post("/api/alert_categories/", formData);
  categoryToAdd.value = {
    name: "",
    text_patterns: "",
    emoji_patterns: "",
    ttl_minutes: 60,
    confirm_threshold: 3,
    deny_threshold: -3,
    enabled: true
  };
  categoryImageToAdd.value = null;
  addImagePreview.value = "";
  await fetchCategories();
}

function onEditCategoryClick(cat) {
  categoryToEdit.value = {
    ...cat,
    text_patterns: joinPatterns(cat.text_patterns),
    emoji_patterns: joinPatterns(cat.emoji_patterns),
    ttl_minutes: cat.ttl_minutes ?? 60,
    confirm_threshold: cat.confirm_threshold ?? 3,
    deny_threshold: cat.deny_threshold ?? -3,
  };
  categoryImageToEdit.value = null;
  editImagePreview.value = resolveImageUrl(cat.image);
}

async function onUpdateCategoryClick() {
  const formData = buildCategoryFormData(categoryToEdit.value, categoryImageToEdit.value);
  await axios.put(`/api/alert_categories/${categoryToEdit.value.id}/`, formData);
  categoryImageToEdit.value = null;
  await fetchCategories();
}

async function onRemoveCategory(cat) {
  await axios.delete(`/api/alert_categories/${cat.id}/`);
  await fetchCategories();
}

function onAddImageChange(event) {
  const file = event.target.files?.[0] || null;
  categoryImageToAdd.value = file;
  addImagePreview.value = file ? URL.createObjectURL(file) : "";
}

function onEditImageChange(event) {
  const file = event.target.files?.[0] || null;
  categoryImageToEdit.value = file;
  if (file) {
    editImagePreview.value = URL.createObjectURL(file);
  }
}

onBeforeMount(() => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  fetchCategories();
});
</script>

<template>
  <div class="container-fluid p-3">
    <h4>Категории событий</h4>

    <!-- Добавление категории -->
    <form @submit.prevent="onAddCategory" class="mb-3">
      <div class="row g-2 align-items-center">
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="categoryToAdd.name" placeholder="Название" required />
            <label>Название</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="categoryToAdd.text_patterns" placeholder="чисто, пусто"
              required />
            <label>Слова (через запятую)</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="categoryToAdd.emoji_patterns"
              placeholder="Эмодзи (через запятую)" required />
            <label>Эмодзи (через запятую)</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="number" class="form-control" v-model="categoryToAdd.ttl_minutes" min="1" />
            <label>TTL (мин)</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="number" class="form-control" v-model="categoryToAdd.confirm_threshold" />
            <label>Порог подтверждения</label>
          </div>
        </div>
        <div class="col">
          <div class="form-floating">
            <input type="number" class="form-control" v-model="categoryToAdd.deny_threshold" />
            <label>Порог отрицания</label>
          </div>
        </div>
        <div class="col-auto">
          <div class="form-check">
            <input type="checkbox" class="form-check-input" v-model="categoryToAdd.enabled" id="enabledAdd">
            <label class="form-check-label" for="enabledAdd">Включён</label>
          </div>
        </div>
        <div class="col">
          <input class="form-control" type="file" accept="image/*" @change="onAddImageChange" />
        </div>
        <div class="col-auto" v-if="addImagePreview">
          <img :src="addImagePreview" alt="preview" class="category-thumb" />
        </div>
        <div class="col-auto">
          <button class="btn btn-primary">Добавить</button>
        </div>
      </div>
    </form>

    <div v-if="loading">Загрузка...</div>

    <div v-else>
      <div v-for="cat in categories" :key="cat.id" class="category-item">

        <div class="category-info">
          <img v-if="cat.image" :src="resolveImageUrl(cat.image)" alt="category" class="category-thumb mb-2" />
          <div class="category-name">{{ cat.name }}</div>
          <div class="category-patterns"><strong>Text:</strong> {{ cat.text_patterns.join(", ") }}</div>
          <div class="category-patterns"><strong>Emoji:</strong> {{ cat.emoji_patterns.join(", ") }}</div>
          <div class="category-patterns"><strong>TTL:</strong> {{ cat.ttl_minutes }} мин</div>
          <div class="category-patterns"><strong>Пороги:</strong> {{ cat.confirm_threshold }} / {{ cat.deny_threshold }}</div>
          <div class="category-status" :class="{ off: !cat.enabled }">{{ cat.enabled ? "Включена" : "Выключена" }}</div>
        </div>

        <div class="category-actions">
          <button class="btn btn-warning" data-bs-toggle="modal" data-bs-target="#editCategoryModal"
            @click="onEditCategoryClick(cat)">
            <i class="bi bi-pen-fill"></i>
          </button>

          <button class="btn btn-danger" @click="onRemoveCategory(cat)">
            <i class="bi bi-trash3-fill"></i>
          </button>
        </div>

      </div>
    </div>

    <!-- Модальное редактирование -->
    <div class="modal fade" id="editCategoryModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">

          <div class="modal-header">
            <h5 class="modal-title">Редактировать категорию</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>

          <div class="modal-body">

            <div class="col">
              <div class="form-floating mb-3">
                <input type="text" class="form-control" v-model="categoryToEdit.name" placeholder="Название" required />
                <label>Название</label>
              </div>
            </div>
            <div class="col">
              <div class="form-floating mb-3">
                <input type="text" class="form-control" v-model="categoryToEdit.text_patterns" placeholder="чисто, пусто"
                  required />
                <label>Слова (через запятую)</label>
              </div>
            </div>
            <div class="col">
              <div class="form-floating mb-3">
                <input type="text" class="form-control" v-model="categoryToEdit.emoji_patterns"
                  placeholder="Эмодзи (через запятую)" required />
                <label>Эмодзи (через запятую)</label>
              </div>
            </div>
            <div class="col">
              <div class="form-floating mb-3">
                <input type="number" class="form-control" v-model="categoryToEdit.ttl_minutes" min="1" />
                <label>TTL (мин)</label>
              </div>
            </div>
            <div class="col">
              <div class="form-floating mb-3">
                <input type="number" class="form-control" v-model="categoryToEdit.confirm_threshold" />
                <label>Порог подтверждения</label>
              </div>
            </div>
            <div class="col">
              <div class="form-floating mb-3">
                <input type="number" class="form-control" v-model="categoryToEdit.deny_threshold" />
                <label>Порог отрицания</label>
              </div>
            </div>
            <div class="col-auto">
              <div class="form-check mb-3">
                <input type="checkbox" class="form-check-input" v-model="categoryToEdit.enabled" id="enabledAdd">
                <label class="form-check-label" for="enabledAdd">Включён</label>
              </div>
            </div>
            <div class="col">
              <label class="form-label">Изображение</label>
              <input class="form-control mb-2" type="file" accept="image/*" @change="onEditImageChange" />
              <img v-if="editImagePreview" :src="editImagePreview" alt="category-preview" class="category-thumb" />
            </div>
            
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
            <button class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateCategoryClick">Сохранить</button>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.category-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .5rem;
  margin: .5rem 0;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.category-info {
  display: flex;
  flex-direction: column;
}

.category-name {
  font-weight: 600;
  font-size: 1.05rem;
}

.category-patterns {
  font-size: .9rem;
}

.category-status {
  font-size: .85rem;
  color: green;
}

.category-status.off {
  color: red;
}

.category-actions {
  display: flex;
  gap: .5rem;
}

.category-thumb {
  width: 44px;
  height: 44px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #ddd;
}
</style>
