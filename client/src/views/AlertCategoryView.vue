<script setup>
import { onMounted, ref } from "vue";
import axios from "axios";

const classes = ref([]);
const items = ref([]);
const loading = ref(false);
const error = ref("");

const form = ref({
  event_class: "",
  name: "",
  text_patterns: "",
  emoji_patterns: "",
  ttl_minutes: 60,
  enabled: true,
  icon: null,
});

const editModalId = "editModal";

const editForm = ref({
  id: null,
  event_class: "",
  name: "",
  text_patterns: "",
  emoji_patterns: "",
  ttl_minutes: 60,
  enabled: true,
  icon: null,
  current_icon: "",
});

function parseList(value) {
  return String(value || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

function resolveMediaUrl(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return path.startsWith("/") ? path : `/${path}`;
}

function onIconChange(e) {
  form.value.icon = e.target.files?.[0] || null;
}

function onEditIconChange(e) {
  editForm.value.icon = e.target.files?.[0] || null;
}

async function loadData() {
  loading.value = true;
  error.value = "";

  try {
    const [c, i] = await Promise.all([
      axios.get("/api/events/event-classes/"),
      axios.get("/api/events/event-class-items/?source_kind=dynamic"),
    ]);

    classes.value = Array.isArray(c.data)
      ? c.data
      : c.data?.results || [];

    items.value = Array.isArray(i.data)
      ? i.data
      : i.data?.results || [];
  } catch (e) {
    error.value =
      e?.response?.data?.detail ||
      "Не удалось загрузить категории парсинга";
  } finally {
    loading.value = false;
  }
}

async function createItem() {
  try {
    const fd = new FormData();

    fd.append(
      "event_class",
      String(Number(form.value.event_class || 0))
    );

    fd.append("name", form.value.name || "");
    fd.append("source_kind", "dynamic");

    fd.append(
      "text_patterns",
      JSON.stringify(parseList(form.value.text_patterns))
    );

    fd.append(
      "emoji_patterns",
      JSON.stringify(parseList(form.value.emoji_patterns))
    );

    fd.append(
      "ttl_minutes",
      String(Number(form.value.ttl_minutes || 60))
    );

    fd.append(
      "enabled",
      form.value.enabled ? "true" : "false"
    );

    if (form.value.icon) {
      fd.append("icon", form.value.icon);
    }

    await axios.post(
      "/api/events/event-class-items/",
      fd,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );

    form.value = {
      event_class: "",
      name: "",
      text_patterns: "",
      emoji_patterns: "",
      ttl_minutes: 60,
      enabled: true,
      icon: null,
    };

    await loadData();
  } catch (e) {
    error.value =
      e?.response?.data?.detail ||
      "Не удалось создать категорию парсинга";
  }
}

function openEditModal(row) {
  editForm.value = {
    id: row.id,
    event_class: row.event_class,
    name: row.name,
    text_patterns: Array.isArray(row.text_patterns)
      ? row.text_patterns.join(", ")
      : "",
    emoji_patterns: Array.isArray(row.emoji_patterns)
      ? row.emoji_patterns.join(", ")
      : "",
    ttl_minutes: row.ttl_minutes,
    enabled: row.enabled,
    icon: null,
    current_icon: row.icon,
  };
}

async function saveEdit() {
  try {
    const fd = new FormData();

    fd.append(
      "event_class",
      String(Number(editForm.value.event_class || 0))
    );

    fd.append("name", editForm.value.name || "");
    fd.append("source_kind", "dynamic");

    fd.append(
      "text_patterns",
      JSON.stringify(parseList(editForm.value.text_patterns))
    );

    fd.append(
      "emoji_patterns",
      JSON.stringify(parseList(editForm.value.emoji_patterns))
    );

    fd.append(
      "ttl_minutes",
      String(Number(editForm.value.ttl_minutes || 60))
    );

    fd.append(
      "enabled",
      editForm.value.enabled ? "true" : "false"
    );

    if (editForm.value.icon) {
      fd.append("icon", editForm.value.icon);
    }

    await axios.patch(
      `/api/events/event-class-items/${editForm.value.id}/`,
      fd,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );

    document
      .querySelector(`#${editModalId}`)
      ?.querySelector('[data-bs-dismiss="modal"]')
      ?.click();

    await loadData();
  } catch (e) {
    error.value =
      e?.response?.data?.detail ||
      "Не удалось сохранить категорию";
  }
}

async function removeRow(id) {
  await axios.delete(`/api/events/event-class-items/${id}/`);
  await loadData();
}

onMounted(async () => {
  await loadData();
});
</script>

<template>
  <div class="page-wrap">

    <div class="page-header mb-4">
      <div>
        <h2 class="page-title">
          <i class="bi bi-cpu-fill me-2"></i>
          Категории парсинга
        </h2>

        <div class="page-subtitle">
          Управление dynamic-категориями событий
        </div>
      </div>
    </div>

    <div v-if="error" class="alert custom-alert">
      <i class="bi bi-exclamation-triangle-fill me-2"></i>
      {{ error }}
    </div>

    <!-- CREATE -->

    <div class="custom-card mb-4">

      <div class="card-title-custom">
        <i class="bi bi-plus-circle-fill me-2"></i>
        Новая категория
      </div>

      <div class="row g-3">

        <div class="col-xl-2 col-lg-3">
          <label class="form-label">Класс</label>

          <select class="form-select custom-input" v-model="form.event_class">
            <option value="">Выберите</option>

            <option v-for="c in classes" :key="c.id" :value="String(c.id)">
              {{ c.name }}
            </option>
          </select>
        </div>

        <div class="col-xl-2 col-lg-3">
          <label class="form-label">Название</label>

          <input class="form-control custom-input" v-model="form.name" />
        </div>

        <div class="col-xl-3">
          <label class="form-label">Ключевые слова</label>

          <input class="form-control custom-input" v-model="form.text_patterns" placeholder="дтп, авария, пробка" />
        </div>

        <div class="col-xl-2">
          <label class="form-label">Эмодзи</label>

          <input class="form-control custom-input" v-model="form.emoji_patterns" />
        </div>

        <div class="col-xl-1 col-lg-2">
          <label class="form-label">TTL</label>

          <input type="number" class="form-control custom-input" v-model.number="form.ttl_minutes" />
        </div>

        <div class="col-xl-2 col-lg-4">
          <label class="form-label">Иконка</label>

          <input type="file" accept="image/*" class="form-control custom-input" @change="onIconChange" />
        </div>

        <div class="col-12 d-flex justify-content-between align-items-center mt-2">

          <div class="form-check custom-check">
            <input class="form-check-input" type="checkbox" id="enabledCreate" v-model="form.enabled" />

            <label class="form-check-label" for="enabledCreate">
              Активна
            </label>
          </div>

          <button class="btn-create" @click="createItem">
            <i class="bi bi-plus-lg me-2"></i>
            Добавить категорию
          </button>

        </div>

      </div>
    </div>

    <!-- TABLE -->

    <div class="custom-card table-card">

      <div class="card-title-custom mb-3">
        <i class="bi bi-list-ul me-2"></i>
        Список категорий
      </div>

      <div class="table-responsive">

        <table class="table align-middle mb-0 custom-table">

          <thead>
            <tr>
              <th>ID</th>
              <th>Иконка</th>
              <th>Название</th>
              <th>Класс</th>
              <th>TTL</th>
              <th>Статус</th>
              <th class="text-end">Действия</th>
            </tr>
          </thead>

          <tbody>

            <tr v-if="loading">
              <td colspan="7" class="text-center py-5">
                Загрузка...
              </td>
            </tr>

            <tr v-for="row in items" :key="row.id">
              <td class="fw-bold">
                #{{ row.id }}
              </td>

              <td>
                <div class="icon-box">
                  <img v-if="row.icon" :src="resolveMediaUrl(row.icon)" class="row-icon" alt="" />

                  <i v-else class="bi bi-image text-muted"></i>
                </div>
              </td>

              <td>
                <div class="fw-semibold">
                  {{ row.name }}
                </div>

                <div class="small text-muted">
                  {{ row.text_patterns?.join(", ") }}
                </div>
              </td>

              <td>
                {{
                  classes.find(x => x.id === row.event_class)?.name || "—"
                }}
              </td>

              <td>
                {{ row.ttl_minutes }} мин
              </td>

              <td>
                <span class="status-badge" :class="row.enabled ? 'active' : 'inactive'">
                  {{ row.enabled ? "Активна" : "Выключена" }}
                </span>
              </td>

              <td>

                <div class="d-flex justify-content-end gap-2">

                  <button class="btn-action btn-edit" data-bs-toggle="modal" :data-bs-target="`#${editModalId}`"
                    @click="openEditModal(row)">
                    <i class="bi bi-pencil-square me-1"></i>
                    Редактировать
                  </button>

                  <button class="btn-action btn-delete" @click="removeRow(row.id)">
                    <i class="bi bi-trash3 me-1"></i>
                    Удалить
                  </button>

                </div>

              </td>
            </tr>

          </tbody>

        </table>

      </div>
    </div>

    <!-- MODAL -->

    <div class="modal fade" id="editModal" tabindex="-1">
      <div class="modal-dialog modal-lg modal-dialog-centered">

        <div class="modal-content custom-modal">

          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title fw-bold">
              Редактирование категории
            </h5>

            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>

          <div class="modal-body">

            <div class="row g-3">

              <div class="col-md-6">
                <label class="form-label">Название</label>

                <input class="form-control custom-input" v-model="editForm.name" />
              </div>

              <div class="col-md-6">
                <label class="form-label">Класс</label>

                <select class="form-select custom-input" v-model="editForm.event_class">
                  <option v-for="c in classes" :key="c.id" :value="c.id">
                    {{ c.name }}
                  </option>
                </select>
              </div>

              <div class="col-md-6">
                <label class="form-label">Слова</label>

                <input class="form-control custom-input" v-model="editForm.text_patterns" />
              </div>

              <div class="col-md-6">
                <label class="form-label">Эмодзи</label>

                <input class="form-control custom-input" v-model="editForm.emoji_patterns" />
              </div>

              <div class="col-md-4">
                <label class="form-label">TTL</label>

                <input type="number" class="form-control custom-input" v-model.number="editForm.ttl_minutes" />
              </div>

              <div class="col-md-4">
                <label class="form-label">Иконка</label>

                <input type="file" accept="image/*" class="form-control custom-input" @change="onEditIconChange" />
              </div>

              <div class="col-md-4 d-flex align-items-end">

                <div class="form-check custom-check mb-2">
                  <input class="form-check-input" type="checkbox" id="editEnabled" v-model="editForm.enabled" />

                  <label class="form-check-label" for="editEnabled">
                    Активна
                  </label>
                </div>

              </div>

              <div v-if="editForm.current_icon" class="col-12">
                <img :src="resolveMediaUrl(editForm.current_icon)" class="preview-icon" />
              </div>

            </div>

          </div>

          <div class="modal-footer border-0 pt-0">
            <button type="button" class="btn-cancel" data-bs-dismiss="modal">
              Отмена
            </button>

            <button type="button" class="btn-save" @click="saveEdit">
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
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.card-title-custom {
  font-size: 18px;
  font-weight: 800;
  margin-bottom: 20px;
  color: #111;
}

.custom-input {
  border-radius: 14px;
  border: 1px solid #dfe3e8;
  padding: 11px 14px;
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

.custom-table thead th {
  border: 0;
  font-size: 13px;
  text-transform: uppercase;
  color: #6c757d;
  padding-bottom: 16px;
}

.custom-table tbody tr {
  border-top: 1px solid #eef1f4;
}

.custom-table td {
  padding: 18px 8px;
  border: 0;
}

.icon-box {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: #f4f7fb;
  display: flex;
  align-items: center;
  justify-content: center;
}

.row-icon {
  width: 32px;
  height: 32px;
  object-fit: contain;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 700;
}

.status-badge.active {
  background: rgba(25, 135, 84, 0.12);
  color: #198754;
}

.status-badge.inactive {
  background: rgba(220, 53, 69, 0.12);
  color: #dc3545;
}

.btn-action {
  border: 0;
  border-radius: 14px;
  padding: 10px 14px;
  font-weight: 700;
  transition: 0.2s ease;
}

.btn-edit {
  background: rgba(13, 110, 253, 0.1);
  color: #0d6efd;
}

.btn-edit:hover {
  background: #0d6efd;
  color: #fff;
}

.btn-delete {
  background: rgba(220, 53, 69, 0.1);
  color: #dc3545;
}

.btn-delete:hover {
  background: #dc3545;
  color: #fff;
}

.custom-modal {
  border: 0;
  border-radius: 24px;
  padding: 10px;
}

.preview-icon {
  width: 70px;
  height: 70px;
  object-fit: contain;
  border-radius: 18px;
  background: #f4f7fb;
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

.custom-alert {
  border: 0;
  border-radius: 18px;
  background: rgba(220, 53, 69, 0.1);
  color: #dc3545;
  font-weight: 600;
}

@media (max-width: 991.98px) {

  .custom-card {
    padding: 18px;
    border-radius: 20px;
  }

  .page-title {
    font-size: 22px;
  }

  .btn-create {
    width: 100%;
    justify-content: center;
  }

  .custom-table {
    min-width: 860px;
  }
}
</style>