<script setup>
import { computed, onMounted, ref, onUnmounted } from "vue";
import axios from "axios";

const classes = ref([]);
const items = ref([]);
const loading = ref(false);
const error = ref("");

// Forms
const classForm = ref({ name: "", sort_order: 0, enabled: true, icon: null });
const itemForm = ref({
  event_class: "",
  name: "",
  source_kind: "static",
  ttl_minutes: 60,
  sort_order: 0,
  enabled: true,
  icon: null,
});

// Edit states
const showEditClassModal = ref(false);
const showEditItemModal = ref(false);
const classEditForm = ref({ name: "", sort_order: 0, enabled: true, icon: null, clear_icon: false });
const itemEditForm = ref({
  event_class: "",
  name: "",
  source_kind: "static",
  ttl_minutes: 60,
  sort_order: 0,
  enabled: true,
  icon: null,
  clear_icon: false,
});
const editingClass = ref(null);
const editingItem = ref(null);

// Dropdown states
const dropdownStates = ref({
  classSort: false,
  itemSort: false,
  itemClass: false,
  itemSourceKind: false,
  editClassSort: false,
  editItemSort: false,
  editItemClass: false,
  editItemSourceKind: false,
  filterClass: false,
});

// Expanded classes for accordion
const expandedClasses = ref({});

// Dropdown container refs
const dropdownRefs = ref({});

const sortOrderOptions = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

// Group items by class
const groupedItems = computed(() => {
  const grouped = {};

  classes.value.forEach(cls => {
    const classItems = items.value.filter(
      item => String(item.event_class) === String(cls.id)
    ).sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));

    grouped[cls.id] = {
      class: cls,
      items: classItems,
    };
  });

  return grouped;
});

function toggleClassAccordion(classId) {
  expandedClasses.value[classId] = !expandedClasses.value[classId];
}

function resolveMediaUrl(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return path.startsWith("/") ? path : `/${path}`;
}

function onClassIconChange(e) {
  classForm.value.icon = e.target.files?.[0] || null;
}

function onItemIconChange(e) {
  itemForm.value.icon = e.target.files?.[0] || null;
}

function onClassEditIconChange(e) {
  classEditForm.value.icon = e.target.files?.[0] || null;
}

function onItemEditIconChange(e) {
  itemEditForm.value.icon = e.target.files?.[0] || null;
}

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    const [c, i] = await Promise.all([
      axios.get("/api/events/event-classes/"),
      axios.get("/api/events/event-class-items/"),
    ]);
    classes.value = (Array.isArray(c.data) ? c.data : c.data?.results || [])
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
    items.value = Array.isArray(i.data) ? i.data : i.data?.results || [];
  } catch (e) {
    error.value = e?.response?.data?.detail || "Ошибка загрузки классификации";
  } finally {
    loading.value = false;
  }
}

async function createClass() {
  try {
    const fd = new FormData();
    fd.append("name", classForm.value.name || "");
    fd.append("sort_order", String(Number(classForm.value.sort_order || 0)));
    fd.append("enabled", classForm.value.enabled ? "true" : "false");
    if (classForm.value.icon) fd.append("icon", classForm.value.icon);
    await axios.post("/api/events/event-classes/", fd, { headers: { "Content-Type": "multipart/form-data" } });
    classForm.value = { name: "", sort_order: 0, enabled: true, icon: null };
    const input = document.getElementById("class-icon-input");
    if (input) input.value = "";
    await loadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось создать класс";
  }
}

async function createItem() {
  try {
    const fd = new FormData();
    fd.append("event_class", String(Number(itemForm.value.event_class)));
    fd.append("name", itemForm.value.name || "");
    fd.append("source_kind", itemForm.value.source_kind);
    if (itemForm.value.source_kind === "dynamic") {
      fd.append("ttl_minutes", String(Number(itemForm.value.ttl_minutes || 60)));
    }
    fd.append("sort_order", String(Number(itemForm.value.sort_order || 0)));
    fd.append("enabled", itemForm.value.enabled ? "true" : "false");
    if (itemForm.value.icon) fd.append("icon", itemForm.value.icon);
    await axios.post("/api/events/event-class-items/", fd, { headers: { "Content-Type": "multipart/form-data" } });
    itemForm.value = {
      event_class: "",
      name: "",
      source_kind: "static",
      ttl_minutes: 60,
      sort_order: 0,
      enabled: true,
      icon: null,
    };
    const input = document.getElementById("item-icon-input");
    if (input) input.value = "";
    await loadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось создать элемент";
  }
}

async function removeClass(id) {
  await axios.delete(`/api/events/event-classes/${id}/`);
  await loadAll();
}

async function removeItem(id) {
  await axios.delete(`/api/events/event-class-items/${id}/`);
  await loadAll();
}

function openEditClassModal(row) {
  editingClass.value = row;
  classEditForm.value = {
    name: row.name || "",
    sort_order: Number(row.sort_order || 0),
    enabled: !!row.enabled,
    icon: null,
    clear_icon: false,
  };
  showEditClassModal.value = true;
}

function closeEditClassModal() {
  showEditClassModal.value = false;
  editingClass.value = null;
}

async function saveEditClass() {
  if (!editingClass.value) return;
  const fd = new FormData();
  fd.append("name", classEditForm.value.name || "");
  fd.append("sort_order", String(Number(classEditForm.value.sort_order || 0)));
  fd.append("enabled", classEditForm.value.enabled ? "true" : "false");
  if (classEditForm.value.clear_icon) fd.append("icon", "");
  if (classEditForm.value.icon) fd.append("icon", classEditForm.value.icon);
  await axios.patch(`/api/events/event-classes/${editingClass.value.id}/`, fd, { headers: { "Content-Type": "multipart/form-data" } });
  closeEditClassModal();
  await loadAll();
}

function openEditItemModal(row) {
  editingItem.value = row;
  itemEditForm.value = {
    event_class: String(row.event_class || ""),
    name: row.name || "",
    source_kind: row.source_kind || "static",
    ttl_minutes: Number(row.ttl_minutes || 60),
    sort_order: Number(row.sort_order || 0),
    enabled: !!row.enabled,
    icon: null,
    clear_icon: false,
  };
  showEditItemModal.value = true;
}

function closeEditItemModal() {
  showEditItemModal.value = false;
  editingItem.value = null;
}

async function saveEditItem() {
  if (!editingItem.value) return;
  const fd = new FormData();
  fd.append("event_class", String(Number(itemEditForm.value.event_class)));
  fd.append("name", itemEditForm.value.name || "");
  fd.append("source_kind", itemEditForm.value.source_kind);
  if (itemEditForm.value.source_kind === "dynamic") {
    fd.append("ttl_minutes", String(Number(itemEditForm.value.ttl_minutes || 60)));
  }
  fd.append("sort_order", String(Number(itemEditForm.value.sort_order || 0)));
  fd.append("enabled", itemEditForm.value.enabled ? "true" : "false");
  if (itemEditForm.value.clear_icon) fd.append("icon", "");
  if (itemEditForm.value.icon) fd.append("icon", itemEditForm.value.icon);
  await axios.patch(`/api/events/event-class-items/${editingItem.value.id}/`, fd, { headers: { "Content-Type": "multipart/form-data" } });
  closeEditItemModal();
  await loadAll();
}

// Dropdown methods
function toggleDropdown(key) {
  const currentState = dropdownStates.value[key];
  Object.keys(dropdownStates.value).forEach(k => {
    dropdownStates.value[k] = false;
  });
  dropdownStates.value[key] = !currentState;
}

function closeAllDropdowns() {
  Object.keys(dropdownStates.value).forEach(k => {
    dropdownStates.value[k] = false;
  });
}

function setDropdownRef(key, el) {
  if (el) {
    dropdownRefs.value[key] = el;
  }
}

function handleClickOutside(event) {
  const target = event.target;
  let clickedInsideDropdown = false;

  Object.keys(dropdownRefs.value).forEach(key => {
    const el = dropdownRefs.value[key];
    if (el && el.contains(target)) {
      clickedInsideDropdown = true;
    }
  });

  if (!clickedInsideDropdown) {
    closeAllDropdowns();
  }
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside, true);
  await loadAll();
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside, true);
});
</script>

<template>
  <div class="page-wrap">

    <!-- HEADER -->
    <div class="page-header mb-4">
      <div>
        <h2 class="page-title">
          <i class="bi bi-diagram-3-fill me-2"></i>
          Классификация событий
        </h2>
        <div class="page-subtitle">
          2-е и 3-е окно добавления событий
        </div>
      </div>
    </div>

    <div v-if="error" class="error-card mb-4">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-exclamation-triangle-fill"></i>
        <span>{{ error }}</span>
      </div>
    </div>

    <!-- ADD CLASS CARD -->
    <div class="custom-card mb-4">
      <div class="card-title-custom">
        <i class="bi bi-plus-circle-fill me-2"></i>
        Новый класс
      </div>
      <div class="row g-3 align-items-end">
        <div class="col-lg-4">
          <label class="form-label">Название класса</label>
          <input class="form-control custom-input" v-model="classForm.name" placeholder="Например: ДТП" />
        </div>
        <div class="col-lg-2">
          <label class="form-label">Порядок</label>
          <div class="main-dropdown" :ref="el => setDropdownRef('classSort', el)">
            <button
              class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
              type="button" @click.stop="toggleDropdown('classSort')">
              <span>{{ classForm.sort_order }}</span>
              <i class="bi bi-chevron-down ms-2"></i>
            </button>
            <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: dropdownStates.classSort }">
              <div class="dropdown-items-scroll">
                <button v-for="value in sortOrderOptions" :key="value" class="dropdown-item-custom"
                  :class="{ active: classForm.sort_order === value }"
                  @click.stop="classForm.sort_order = value; closeAllDropdowns()">
                  {{ value }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="col-lg-3">
          <label class="form-label">Иконка</label>
          <div class="file-upload-wrapper">
            <input id="class-icon-input" class="form-control custom-input file-input-hidden" type="file"
              accept="image/*" @change="onClassIconChange" />
            <label for="class-icon-input" class="file-upload-label">
              <i class="bi bi-image me-2"></i>
              <span v-if="classForm.icon">{{ classForm.icon.name }}</span>
              <span v-else class="text-muted">Выберите иконку</span>
            </label>
          </div>
        </div>
        <div class="col-lg-2 d-flex align-items-end gap-3">
          <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" id="class-enabled" v-model="classForm.enabled" />
            <label class="form-check-label fw-semibold" for="class-enabled">Активен</label>
          </div>
        </div>
        <div class="col-lg-2">
          <button class="btn-create w-100" @click="createClass">
            <i class="bi bi-plus-lg"></i>
            Добавить
          </button>
        </div>
      </div>
    </div>

    <!-- ADD ITEM CARD -->
    <div class="custom-card mb-4">
      <div class="card-title-custom">
        <i class="bi bi-plus-circle-fill me-2"></i>
        Новая категория
      </div>
      <div class="row g-3 align-items-end">
        <div class="col-lg-3">
          <label class="form-label">Класс (группа)</label>
          <div class="main-dropdown" :ref="el => setDropdownRef('itemClass', el)">
            <button
              class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
              type="button" @click.stop="toggleDropdown('itemClass')">
              <span v-if="itemForm.event_class">
                {{classes.find(c => String(c.id) === itemForm.event_class)?.name || 'Выбран'}}
              </span>
              <span v-else class="text-muted">Выберите класс</span>
              <i class="bi bi-chevron-down ms-2"></i>
            </button>
            <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: dropdownStates.itemClass }">
              <div class="dropdown-items-scroll">
                <button v-for="c in classes" :key="c.id" class="dropdown-item-custom"
                  :class="{ active: itemForm.event_class === String(c.id) }"
                  @click.stop="itemForm.event_class = String(c.id); closeAllDropdowns()">
                  {{ c.name }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="col-lg-3">
          <label class="form-label">Название категории</label>
          <input class="form-control custom-input" v-model="itemForm.name" placeholder="Например: Авария" />
        </div>
        <div class="col-lg-2">
          <label class="form-label">Тип источника</label>
          <div class="main-dropdown" :ref="el => setDropdownRef('itemSourceKind', el)">
            <button
              class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
              type="button" @click.stop="toggleDropdown('itemSourceKind')">
              <span>{{ itemForm.source_kind === 'static' ? 'Статический' : 'Динамический' }}</span>
              <i class="bi bi-chevron-down ms-2"></i>
            </button>
            <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: dropdownStates.itemSourceKind }">
              <div class="dropdown-items-scroll">
                <button class="dropdown-item-custom" :class="{ active: itemForm.source_kind === 'static' }"
                  @click.stop="itemForm.source_kind = 'static'; closeAllDropdowns()">
                  Статический
                </button>
                <button class="dropdown-item-custom" :class="{ active: itemForm.source_kind === 'dynamic' }"
                  @click.stop="itemForm.source_kind = 'dynamic'; closeAllDropdowns()">
                  Динамический
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="col-lg-2">
          <label class="form-label">Порядок</label>
          <div class="main-dropdown" :ref="el => setDropdownRef('itemSort', el)">
            <button
              class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
              type="button" @click.stop="toggleDropdown('itemSort')">
              <span>{{ itemForm.sort_order }}</span>
              <i class="bi bi-chevron-down ms-2"></i>
            </button>
            <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: dropdownStates.itemSort }">
              <div class="dropdown-items-scroll">
                <button v-for="value in sortOrderOptions" :key="value" class="dropdown-item-custom"
                  :class="{ active: itemForm.sort_order === value }"
                  @click.stop="itemForm.sort_order = value; closeAllDropdowns()">
                  {{ value }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="col-lg-3">
          <label class="form-label">Иконка</label>
          <div class="file-upload-wrapper">
            <input id="item-icon-input" class="form-control custom-input file-input-hidden" type="file" accept="image/*"
              @change="onItemIconChange" />
            <label for="item-icon-input" class="file-upload-label">
              <i class="bi bi-image me-2"></i>
              <span v-if="itemForm.icon">{{ itemForm.icon.name }}</span>
              <span v-else class="text-muted">Выберите иконку</span>
            </label>
          </div>
        </div>
        <div class="col-lg-2 d-flex align-items-end gap-3">
          <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" id="item-enabled" v-model="itemForm.enabled" />
            <label class="form-check-label fw-semibold" for="item-enabled">Активен</label>
          </div>
        </div>
        <div class="col-lg-2">
          <button class="btn-create w-100" @click="createItem">
            <i class="bi bi-plus-lg"></i>
            Добавить
          </button>
        </div>
      </div>
    </div>

    <!-- CLASSES & ITEMS ACCORDION -->
    <!-- CLASSES & ITEMS ACCORDION -->
    <div class="custom-card">
      <div class="card-title-custom mb-4">
        <i class="bi bi-list-ul me-2"></i>
        Категории по классам
      </div>

      <div v-if="loading" class="loading-box">
        Загрузка...
      </div>

      <div v-else-if="classes.length === 0" class="empty-box">
        <i class="bi bi-inbox me-2"></i>
        Классов пока нет
      </div>

      <div v-else class="accordion-list">
        <div v-for="cls in classes" :key="cls.id" class="accordion-item-custom">
          <!-- Class Header -->
          <div class="accordion-header-custom" :class="{ expanded: expandedClasses[cls.id] }"
            @click="toggleClassAccordion(cls.id)">
            <div class="accordion-header-left">
              <div class="accordion-icon-wrapper">
                <img v-if="cls.icon" :src="resolveMediaUrl(cls.icon)" class="accordion-icon" alt="" />
                <i v-else class="bi bi-folder-fill accordion-icon-placeholder"></i>
              </div>
              <div class="accordion-header-info">
                <div class="accordion-class-name">{{ cls.name }}</div>
                <div class="accordion-class-meta">
                  <span>Порядок: {{ cls.sort_order }}</span>
                  <span class="accordion-item-count">
                    {{ groupedItems[cls.id]?.items.length || 0 }} категорий
                  </span>
                </div>
              </div>
            </div>
            <div class="accordion-header-right">
              <span class="class-status-badge" :class="cls.enabled ? 'enabled' : 'disabled'">
                {{ cls.enabled ? 'Активен' : 'Неактивен' }}
              </span>
              <button class="btn-action btn-edit" @click.stop="openEditClassModal(cls)">
                <i class="bi bi-pencil-square me-1"></i>
                Ред.
              </button>
              <button class="btn-action btn-delete" @click.stop="removeClass(cls.id)">
                <i class="bi bi-trash3 me-1"></i>
                Удалить
              </button>
              <i class="bi chevron-icon" :class="expandedClasses[cls.id] ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
            </div>
          </div>

          <!-- Items List -->
          <transition name="accordion">
            <div v-if="expandedClasses[cls.id]" class="accordion-body-custom">
              <div v-if="groupedItems[cls.id]?.items.length === 0" class="empty-items">
                <i class="bi bi-inbox me-2"></i>
                Нет категорий в этом классе
              </div>
              <div v-else class="items-list">
                <div v-for="item in groupedItems[cls.id].items" :key="item.id" class="item-row">
                  <div class="item-row-left">
                    <div class="item-icon-small">
                      <img v-if="item.icon" :src="resolveMediaUrl(item.icon)" class="item-img-small" alt="" />
                      <i v-else class="bi bi-tag-fill item-icon-placeholder"></i>
                    </div>
                    <div class="item-row-info">
                      <div class="item-row-name">{{ item.name }}</div>
                      <div class="item-row-meta">
                        <span class="item-kind">{{ item.source_kind === 'static' ? 'Статический' : 'Динамический'
                        }}</span>
                        <span class="item-order">Порядок: {{ item.sort_order }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="item-row-right">
                    <span class="item-status-badge" :class="item.enabled ? 'enabled' : 'disabled'">
                      {{ item.enabled ? 'Активна' : 'Неактивна' }}
                    </span>
                    <button class="btn-action btn-edit" @click.stop="openEditItemModal(item)">
                      <i class="bi bi-pencil-square me-1"></i>
                      Ред.
                    </button>
                    <button class="btn-action btn-delete" @click.stop="removeItem(item.id)">
                      <i class="bi bi-trash3 me-1"></i>
                      Удалить
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </div>

    <!-- EDIT CLASS MODAL -->
    <transition name="fade">
      <div v-if="showEditClassModal" class="modal-overlay" @click.self="closeEditClassModal">
        <div class="modal-dialog-custom">
          <div class="custom-modal">
            <div class="modal-header border-0 pb-0">
              <h5 class="modal-title fw-bold">Редактировать класс</h5>
              <button type="button" class="btn-close" @click="closeEditClassModal"></button>
            </div>
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label">Название</label>
                <input class="form-control custom-input" v-model="classEditForm.name" />
              </div>
              <div class="mb-3">
                <label class="form-label">Порядок</label>
                <div class="main-dropdown" :ref="el => setDropdownRef('editClassSort', el)">
                  <button
                    class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
                    type="button" @click.stop="toggleDropdown('editClassSort')">
                    <span>{{ classEditForm.sort_order }}</span>
                    <i class="bi bi-chevron-down ms-2"></i>
                  </button>
                  <div class="dropdown-menu custom-menu shadow border-0"
                    :class="{ show: dropdownStates.editClassSort }">
                    <div class="dropdown-items-scroll">
                      <button v-for="value in sortOrderOptions" :key="value" class="dropdown-item-custom"
                        :class="{ active: classEditForm.sort_order === value }"
                        @click.stop="classEditForm.sort_order = value; closeAllDropdowns()">
                        {{ value }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label">Иконка</label>
                <div class="file-upload-wrapper">
                  <input id="edit-class-icon" class="form-control custom-input file-input-hidden" type="file"
                    accept="image/*" @change="onClassEditIconChange" />
                  <label for="edit-class-icon" class="file-upload-label">
                    <i class="bi bi-image me-2"></i>
                    <span v-if="classEditForm.icon">{{ classEditForm.icon.name }}</span>
                    <span v-else class="text-muted">Выберите новую иконку</span>
                  </label>
                </div>
              </div>
              <div class="mb-3">
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="edit-class-enabled"
                    v-model="classEditForm.enabled" />
                  <label class="form-check-label fw-semibold" for="edit-class-enabled">Активен</label>
                </div>
              </div>
              <div class="mb-0">
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="edit-class-clear-icon"
                    v-model="classEditForm.clear_icon" />
                  <label class="form-check-label fw-semibold" for="edit-class-clear-icon">Убрать иконку</label>
                </div>
              </div>
            </div>
            <div class="modal-footer border-0 pt-0">
              <button class="btn-cancel" @click="closeEditClassModal">Отмена</button>
              <button class="btn-save" @click="saveEditClass">Сохранить</button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- EDIT ITEM MODAL -->
    <transition name="fade">
      <div v-if="showEditItemModal" class="modal-overlay" @click.self="closeEditItemModal">
        <div class="modal-dialog-custom">
          <div class="custom-modal">
            <div class="modal-header border-0 pb-0">
              <h5 class="modal-title fw-bold">Редактировать категорию</h5>
              <button type="button" class="btn-close" @click="closeEditItemModal"></button>
            </div>
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label">Класс</label>
                <div class="main-dropdown" :ref="el => setDropdownRef('editItemClass', el)">
                  <button
                    class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
                    type="button" @click.stop="toggleDropdown('editItemClass')">
                    <span>{{classes.find(c => String(c.id) === itemEditForm.event_class)?.name || 'Выберите класс'
                    }}</span>
                    <i class="bi bi-chevron-down ms-2"></i>
                  </button>
                  <div class="dropdown-menu custom-menu shadow border-0"
                    :class="{ show: dropdownStates.editItemClass }">
                    <div class="dropdown-items-scroll">
                      <button v-for="c in classes" :key="c.id" class="dropdown-item-custom"
                        :class="{ active: itemEditForm.event_class === String(c.id) }"
                        @click.stop="itemEditForm.event_class = String(c.id); closeAllDropdowns()">
                        {{ c.name }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label">Название</label>
                <input class="form-control custom-input" v-model="itemEditForm.name" />
              </div>
              <div class="mb-3">
                <label class="form-label">Тип источника</label>
                <div class="main-dropdown" :ref="el => setDropdownRef('editItemSourceKind', el)">
                  <button
                    class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
                    type="button" @click.stop="toggleDropdown('editItemSourceKind')">
                    <span>{{ itemEditForm.source_kind === 'static' ? 'Статический' : 'Динамический' }}</span>
                    <i class="bi bi-chevron-down ms-2"></i>
                  </button>
                  <div class="dropdown-menu custom-menu shadow border-0"
                    :class="{ show: dropdownStates.editItemSourceKind }">
                    <div class="dropdown-items-scroll">
                      <button class="dropdown-item-custom" :class="{ active: itemEditForm.source_kind === 'static' }"
                        @click.stop="itemEditForm.source_kind = 'static'; closeAllDropdowns()">
                        Статический
                      </button>
                      <button class="dropdown-item-custom" :class="{ active: itemEditForm.source_kind === 'dynamic' }"
                        @click.stop="itemEditForm.source_kind = 'dynamic'; closeAllDropdowns()">
                        Динамический
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label">Порядок</label>
                <div class="main-dropdown" :ref="el => setDropdownRef('editItemSort', el)">
                  <button
                    class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
                    type="button" @click.stop="toggleDropdown('editItemSort')">
                    <span>{{ itemEditForm.sort_order }}</span>
                    <i class="bi bi-chevron-down ms-2"></i>
                  </button>
                  <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: dropdownStates.editItemSort }">
                    <div class="dropdown-items-scroll">
                      <button v-for="value in sortOrderOptions" :key="value" class="dropdown-item-custom"
                        :class="{ active: itemEditForm.sort_order === value }"
                        @click.stop="itemEditForm.sort_order = value; closeAllDropdowns()">
                        {{ value }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label">Иконка</label>
                <div class="file-upload-wrapper">
                  <input id="edit-item-icon" class="form-control custom-input file-input-hidden" type="file"
                    accept="image/*" @change="onItemEditIconChange" />
                  <label for="edit-item-icon" class="file-upload-label">
                    <i class="bi bi-image me-2"></i>
                    <span v-if="itemEditForm.icon">{{ itemEditForm.icon.name }}</span>
                    <span v-else class="text-muted">Выберите новую иконку</span>
                  </label>
                </div>
              </div>
              <div class="mb-3">
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="edit-item-enabled"
                    v-model="itemEditForm.enabled" />
                  <label class="form-check-label fw-semibold" for="edit-item-enabled">Активна</label>
                </div>
              </div>
              <div class="mb-0">
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="edit-item-clear-icon"
                    v-model="itemEditForm.clear_icon" />
                  <label class="form-check-label fw-semibold" for="edit-item-clear-icon">Убрать иконку</label>
                </div>
              </div>
            </div>
            <div class="modal-footer border-0 pt-0">
              <button class="btn-cancel" @click="closeEditItemModal">Отмена</button>
              <button class="btn-save" @click="saveEditItem">Сохранить</button>
            </div>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>

<style scoped>
/* Общие стили */
.page-wrap,
.row,
.col-lg-2,
.col-lg-3,
.col-lg-4,
.col-md-2,
.col-md-3,
.col-md-4,
[class*="col-"] {
  overflow: visible !important;
}

form {
  overflow: visible !important;
}

.g-3 {
  overflow: visible !important;
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
  position: relative;
  z-index: 1;
  overflow: visible !important;
}

.custom-card:has(.custom-menu.show) {
  z-index: 5000;
  overflow: visible !important;
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
  background: #fff;
}

.custom-input:focus {
  border-color: #0d6efd;
}

/* Кнопки */
.btn-create {
  border: 0;
  background: #0d6efd;
  color: #fff;
  padding: 12px 20px;
  border-radius: 14px;
  font-weight: 700;
  transition: 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  white-space: nowrap;
}

.btn-create:hover:not(:disabled) {
  background: #0b5ed7;
  transform: translateY(-1px);
}

.btn-action {
  border: 0;
  border-radius: 14px;
  padding: 10px 14px;
  font-weight: 700;
  transition: 0.2s ease;
  white-space: nowrap;
  font-size: 14px;
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

.btn-filter {
  border: 0;
  background: rgba(13, 110, 253, 0.1);
  color: #0d6efd;
  padding: 10px 16px;
  border-radius: 14px;
  font-weight: 700;
  transition: 0.2s ease;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-filter:hover {
  background: rgba(13, 110, 253, 0.2);
}

/* File upload */
.file-upload-wrapper {
  position: relative;
}

.file-input-hidden {
  position: absolute;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
  z-index: 2;
}

.file-upload-label {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #dfe3e8;
  background: #fff;
  cursor: pointer;
  font-weight: 500;
  transition: 0.2s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-upload-label:hover {
  border-color: #0d6efd;
}

/* ===== DROPDOWN STYLES ===== */
.main-dropdown {
  position: relative;
  z-index: auto;
}

.main-dropdown:has(.custom-menu.show) {
  z-index: 9999;
}

.dropdown-toggle-btn {
  cursor: pointer;
  user-select: none;
  background: #fff;
  transition: all 0.2s ease;
}

.dropdown-toggle-btn:hover {
  border-color: #0d6efd;
}

.custom-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: auto;
  min-width: 100%;
  max-height: 250px;
  padding: 8px;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.35), 0 4px 12px rgba(15, 23, 42, 0.15);
  opacity: 0;
  visibility: hidden;
  transform: translateY(-8px);
  display: block;
  pointer-events: none;
  transition: opacity 0.2s ease, visibility 0.2s ease, transform 0.2s ease;
  z-index: 9999 !important;
}

.filter-dropdown {
  right: 0;
  left: auto;
  min-width: 220px;
}

.main-dropdown .custom-menu.show {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transform: translateY(0);
}

.dropdown-items-scroll {
  max-height: 220px;
  overflow-y: auto;
}

.dropdown-item-custom {
  display: flex;
  align-items: center;
  width: 100%;
  border: 0;
  background: transparent;
  border-radius: 12px;
  padding: 11px 14px;
  font-weight: 600;
  font-size: 14px;
  color: #111;
  transition: all 0.18s ease;
  cursor: pointer;
  text-align: left;
  margin-bottom: 2px;
}

.dropdown-item-custom:hover {
  background: #f0f4ff;
  transform: translateX(2px);
}

.dropdown-item-custom.active {
  background: rgba(13, 110, 253, 0.08);
  color: #0d6efd;
}

.dropdown-items-scroll::-webkit-scrollbar {
  width: 5px;
}

.dropdown-items-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.dropdown-items-scroll::-webkit-scrollbar-thumb {
  background: #dfe3e8;
  border-radius: 3px;
}

.dropdown-items-scroll::-webkit-scrollbar-thumb:hover {
  background: #c1c7cd;
}

/* Error card */
.error-card {
  background: rgba(220, 53, 69, 0.08);
  border: 1px solid rgba(220, 53, 69, 0.2);
  border-radius: 16px;
  padding: 14px 18px;
  color: #dc3545;
  font-weight: 600;
  font-size: 14px;
}

/* Classes grid */
.classes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}

.class-card {
  border-radius: 20px;
  background: #f8fafc;
  border: 1px solid #eef1f4;
  padding: 18px;
  text-align: center;
  transition: 0.2s ease;
}

.class-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.class-icon-wrapper {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: rgba(13, 110, 253, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 10px;
  overflow: hidden;
}

.class-icon {
  width: 36px;
  height: 36px;
  object-fit: contain;
}

.class-icon-placeholder {
  font-size: 24px;
  color: #0d6efd;
}

.class-name {
  font-size: 15px;
  font-weight: 700;
  color: #111;
  margin-bottom: 8px;
}

.class-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
  margin-bottom: 12px;
  font-size: 13px;
}

.class-order {
  color: #6c757d;
}

.class-status-badge {
  padding: 4px 12px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 12px;
}

.class-status-badge.enabled {
  background: rgba(25, 135, 84, 0.1);
  color: #198754;
}

.class-status-badge.disabled {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

.class-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

/* Categories grid */
.categories-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.category-card {
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

.category-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.category-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 0;
}

.category-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: rgba(111, 66, 193, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.category-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.category-icon-placeholder {
  font-size: 20px;
  color: #6f42c1;
}

.category-info {
  min-width: 0;
  flex: 1;
}

.category-name {
  font-size: 16px;
  font-weight: 700;
  color: #111;
  margin-bottom: 4px;
}

.category-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 13px;
  color: #6c757d;
}

.category-class {
  font-weight: 600;
  color: #0d6efd;
}

.category-kind {
  color: #6c757d;
}

.category-key {
  font-family: 'Courier New', monospace;
  color: #198754;
}

.category-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
  flex-shrink: 0;
}

.category-order {
  font-size: 13px;
  color: #6c757d;
}

.category-status-badge {
  padding: 4px 12px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 12px;
}

.category-status-badge.enabled {
  background: rgba(25, 135, 84, 0.1);
  color: #198754;
}

.category-status-badge.disabled {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

.item-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

/* States */
.loading-box,
.empty-box {
  padding: 40px;
  text-align: center;
  color: #6c757d;
  font-weight: 600;
  grid-column: 1 / -1;
}

/* Modal overlay */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal-dialog-custom {
  width: 520px;
  max-width: calc(100vw - 24px);
  margin: 16px;
}

.custom-modal {
  background: #fff;
  border-radius: 24px;
  padding: 10px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.2);
}

.btn-cancel,
.btn-save {
  border: 0;
  border-radius: 14px;
  padding: 12px 20px;
  font-weight: 700;
  transition: 0.2s ease;
}

.btn-cancel {
  background: #eef1f4;
}

.btn-cancel:hover {
  background: #dfe3e8;
}

.btn-save {
  background: #0d6efd;
  color: #fff;
}

.btn-save:hover {
  background: #0b5ed7;
}

/* Animation */
.fade-enter-active,
.fade-leave-active {
  transition: 0.22s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-enter-from .modal-dialog-custom,
.fade-leave-to .modal-dialog-custom {
  transform: scale(0.96);
}

/* Адаптив */
@media (max-width: 991.98px) {
  .custom-card {
    padding: 18px;
    border-radius: 20px;
  }

  .page-title {
    font-size: 22px;
  }

  .classes-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  }

  .category-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .category-details {
    flex-direction: row;
    gap: 12px;
    align-items: center;
  }

  .item-actions {
    width: 100%;
    flex-direction: column;
  }

  .btn-action {
    width: 100%;
    justify-content: center;
  }
}

/* ===== ACCORDION STYLES ===== */
.accordion-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.accordion-item-custom {
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #eef1f4;
  overflow: hidden;
  transition: 0.2s ease;
}

.accordion-item-custom:hover {
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}

.accordion-header-custom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
  transition: 0.2s ease;
}

.accordion-header-custom:hover {
  background: rgba(13, 110, 253, 0.02);
}

.accordion-header-custom.expanded {
  background: rgba(13, 110, 253, 0.03);
  border-bottom: 1px solid #eef1f4;
}

.accordion-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 0;
}

.accordion-icon-wrapper {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: rgba(13, 110, 253, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.accordion-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.accordion-icon-placeholder {
  font-size: 20px;
  color: #0d6efd;
}

.accordion-header-info {
  min-width: 0;
}

.accordion-class-name {
  font-size: 16px;
  font-weight: 700;
  color: #111;
  margin-bottom: 2px;
}

.accordion-class-meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #6c757d;
}

.accordion-item-count {
  background: rgba(13, 110, 253, 0.08);
  color: #0d6efd;
  padding: 2px 8px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 12px;
}

.accordion-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.chevron-icon {
  font-size: 18px;
  color: #6c757d;
  transition: transform 0.2s ease;
}

.class-status-badge {
  padding: 4px 12px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 12px;
  white-space: nowrap;
}

.class-status-badge.enabled {
  background: rgba(25, 135, 84, 0.1);
  color: #198754;
}

.class-status-badge.disabled {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

/* Accordion Body */
.accordion-body-custom {
  padding: 8px 20px 16px;
}

.empty-items {
  padding: 24px;
  text-align: center;
  color: #6c757d;
  font-weight: 600;
  font-size: 14px;
}

.items-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #eef1f4;
  transition: 0.15s ease;
}

.item-row:hover {
  border-color: #dfe3e8;
  transform: translateX(2px);
}

.item-row-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.item-icon-small {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: rgba(111, 66, 193, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.item-img-small {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.item-icon-placeholder {
  font-size: 16px;
  color: #6f42c1;
}

.item-row-info {
  min-width: 0;
}

.item-row-name {
  font-size: 14px;
  font-weight: 700;
  color: #111;
  margin-bottom: 2px;
}

.item-row-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #6c757d;
}

.item-kind {
  font-weight: 600;
  color: #0d6efd;
}

.item-key {
  font-family: 'Courier New', monospace;
  color: #198754;
}

.item-order {
  color: #6c757d;
}

.item-row-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.item-status-badge {
  padding: 3px 10px;
  border-radius: 8px;
  font-weight: 700;
  font-size: 11px;
  white-space: nowrap;
}

.item-status-badge.enabled {
  background: rgba(25, 135, 84, 0.1);
  color: #198754;
}

.item-status-badge.disabled {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

/* Accordion animation */
.accordion-enter-active {
  transition: all 0.25s ease-out;
}

.accordion-leave-active {
  transition: all 0.2s ease-in;
}

.accordion-enter-from {
  opacity: 0;
  max-height: 0;
}

.accordion-enter-to {
  opacity: 1;
  max-height: 2000px;
}

.accordion-leave-from {
  opacity: 1;
  max-height: 2000px;
}

.accordion-leave-to {
  opacity: 0;
  max-height: 0;
}

/* Убираем старые стили для classes-grid и categories-grid */
.classes-grid,
.categories-grid {
  display: none;
}
</style>
