<script setup>
import { computed, onBeforeMount, ref } from "vue";
import axios from "axios";
import Cookies from "js-cookie";

const isLoading = ref(false);
const message = ref("");
const error = ref("");
const regions = ref([]);
const cities = ref([]);

const regionForm = ref({ name: "" });
const cityForm = ref({ name: "", region: "" });
const editRegion = ref({ id: null, name: "" });
const editCity = ref({ id: null, name: "", region: "" });

const sortedRegions = computed(() => {
  return [...regions.value].sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "ru"));
});

const sortedCities = computed(() => {
  return [...cities.value].sort((a, b) => {
    const regionCompare = String(a.region_name || "").localeCompare(String(b.region_name || ""), "ru");
    if (regionCompare !== 0) return regionCompare;
    return String(a.name || "").localeCompare(String(b.name || ""), "ru");
  });
});

function clearStatus() {
  message.value = "";
  error.value = "";
}

async function loadData() {
  isLoading.value = true;
  clearStatus();
  try {
    const [regionsRes, citiesRes] = await Promise.all([
      axios.get("/api/regions/"),
      axios.get("/api/cities/"),
    ]);
    regions.value = Array.isArray(regionsRes.data) ? regionsRes.data : [];
    cities.value = Array.isArray(citiesRes.data) ? citiesRes.data : [];
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось загрузить справочники областей и городов.";
  } finally {
    isLoading.value = false;
  }
}

async function createRegion() {
  const name = regionForm.value.name.trim();
  if (!name) return;
  clearStatus();
  try {
    await axios.post("/api/regions/", { name });
    regionForm.value.name = "";
    message.value = "Область добавлена.";
    await loadData();
  } catch (e) {
    error.value = e?.response?.data?.name?.[0] || e?.response?.data?.detail || "Не удалось добавить область.";
  }
}

function openEditRegion(region) {
  editRegion.value = { id: region.id, name: region.name || "" };
}

async function updateRegion() {
  const name = editRegion.value.name.trim();
  if (!editRegion.value.id || !name) return;
  clearStatus();
  try {
    await axios.patch(`/api/regions/${editRegion.value.id}/`, { name });
    message.value = "Область обновлена.";
    await loadData();
  } catch (e) {
    error.value = e?.response?.data?.name?.[0] || e?.response?.data?.detail || "Не удалось обновить область.";
  }
}

async function removeRegion(region) {
  if (!confirm(`Удалить область «${region.name}»? Города этой области тоже будут удалены.`)) return;
  clearStatus();
  try {
    await axios.delete(`/api/regions/${region.id}/`);
    message.value = "Область удалена.";
    await loadData();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось удалить область.";
  }
}

async function createCity() {
  const name = cityForm.value.name.trim();
  const region = Number(cityForm.value.region);
  if (!name || !region) return;
  clearStatus();
  try {
    await axios.post("/api/cities/", { name, region });
    cityForm.value = { name: "", region: "" };
    message.value = "Город добавлен.";
    await loadData();
  } catch (e) {
    error.value = e?.response?.data?.name?.[0] || e?.response?.data?.detail || "Не удалось добавить город.";
  }
}

function openEditCity(city) {
  editCity.value = { id: city.id, name: city.name || "", region: city.region || "" };
}

async function updateCity() {
  const name = editCity.value.name.trim();
  const region = Number(editCity.value.region);
  if (!editCity.value.id || !name || !region) return;
  clearStatus();
  try {
    await axios.patch(`/api/cities/${editCity.value.id}/`, { name, region });
    message.value = "Город обновлен.";
    await loadData();
  } catch (e) {
    error.value = e?.response?.data?.name?.[0] || e?.response?.data?.detail || "Не удалось обновить город.";
  }
}

async function removeCity(city) {
  if (!confirm(`Удалить город «${city.name}»?`)) return;
  clearStatus();
  try {
    await axios.delete(`/api/cities/${city.id}/`);
    message.value = "Город удален.";
    await loadData();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось удалить город.";
  }
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await loadData();
});
</script>

<template>
  <div class="directory-page">
    <header class="page-header">
      <div>
        <h2 class="page-title">
          <i class="bi bi-buildings me-2"></i>
          Области и города
        </h2>
        <div class="page-subtitle">Справочники географической привязки без хранения полигонов</div>
      </div>
      <button class="icon-btn" :disabled="isLoading" @click="loadData">
        <i class="bi bi-arrow-clockwise"></i>
      </button>
    </header>

    <div v-if="message" class="status-card success">
      <i class="bi bi-check-circle-fill"></i>
      {{ message }}
    </div>
    <div v-if="error" class="status-card danger">
      <i class="bi bi-exclamation-triangle-fill"></i>
      {{ error }}
    </div>

    <section class="grid-forms">
      <form class="custom-card" @submit.prevent="createRegion">
        <div class="card-title-custom">
          <i class="bi bi-plus-circle me-2"></i>
          Новая область
        </div>
        <div class="form-row">
          <input v-model="regionForm.name" class="custom-input" placeholder="Название области" />
          <button class="btn-create" :disabled="!regionForm.name.trim()">Добавить</button>
        </div>
      </form>

      <form class="custom-card" @submit.prevent="createCity">
        <div class="card-title-custom">
          <i class="bi bi-plus-circle me-2"></i>
          Новый город
        </div>
        <div class="form-row city-row">
          <select v-model="cityForm.region" class="custom-input">
            <option value="">Выберите область</option>
            <option v-for="region in sortedRegions" :key="region.id" :value="region.id">
              {{ region.name }}
            </option>
          </select>
          <input v-model="cityForm.name" class="custom-input" placeholder="Название города" />
          <button class="btn-create" :disabled="!cityForm.name.trim() || !cityForm.region">Добавить</button>
        </div>
      </form>
    </section>

    <section class="custom-card">
      <div class="section-head">
        <div class="card-title-custom mb-0">
          <i class="bi bi-map me-2"></i>
          Области
        </div>
        <span class="counter">{{ sortedRegions.length }}</span>
      </div>

      <div v-if="isLoading" class="empty-box">Загрузка...</div>
      <div v-else-if="sortedRegions.length === 0" class="empty-box">Областей пока нет</div>
      <div v-else class="items-grid">
        <article v-for="region in sortedRegions" :key="region.id" class="directory-item">
          <div class="item-main">
            <div class="item-icon"><i class="bi bi-hexagon-fill"></i></div>
            <div>
              <div class="item-title">{{ region.name }}</div>
              <div class="item-subtitle">Городов: {{ cities.filter((city) => city.region === region.id).length }}</div>
            </div>
          </div>
          <div class="item-actions">
            <button class="btn-action btn-edit" data-bs-toggle="modal" data-bs-target="#editRegionModal" @click="openEditRegion(region)">
              <i class="bi bi-pencil-square"></i>
            </button>
            <button class="btn-action btn-delete" @click="removeRegion(region)">
              <i class="bi bi-trash3"></i>
            </button>
          </div>
        </article>
      </div>
    </section>

    <section class="custom-card">
      <div class="section-head">
        <div class="card-title-custom mb-0">
          <i class="bi bi-buildings me-2"></i>
          Города
        </div>
        <span class="counter">{{ sortedCities.length }}</span>
      </div>

      <div v-if="isLoading" class="empty-box">Загрузка...</div>
      <div v-else-if="sortedCities.length === 0" class="empty-box">Городов пока нет</div>
      <div v-else class="table-wrap">
        <table class="directory-table">
          <thead>
            <tr>
              <th>Город</th>
              <th>Область</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="city in sortedCities" :key="city.id">
              <td>{{ city.name }}</td>
              <td>{{ city.region_name || "—" }}</td>
              <td class="table-actions">
                <button class="btn-action btn-edit" data-bs-toggle="modal" data-bs-target="#editCityModal" @click="openEditCity(city)">
                  <i class="bi bi-pencil-square"></i>
                </button>
                <button class="btn-action btn-delete" @click="removeCity(city)">
                  <i class="bi bi-trash3"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div class="modal fade" id="editRegionModal" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content custom-modal">
          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title fw-bold">Редактировать область</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <label class="form-label">Название области</label>
            <input v-model="editRegion.name" class="form-control custom-input" />
          </div>
          <div class="modal-footer border-0 pt-0">
            <button class="btn-cancel" data-bs-dismiss="modal">Отмена</button>
            <button class="btn-save" data-bs-dismiss="modal" @click="updateRegion">Сохранить</button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" id="editCityModal" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content custom-modal">
          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title fw-bold">Редактировать город</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body modal-grid">
            <label class="form-label">Область</label>
            <select v-model="editCity.region" class="form-control custom-input">
              <option v-for="region in sortedRegions" :key="region.id" :value="region.id">
                {{ region.name }}
              </option>
            </select>
            <label class="form-label">Название города</label>
            <input v-model="editCity.name" class="form-control custom-input" />
          </div>
          <div class="modal-footer border-0 pt-0">
            <button class="btn-cancel" data-bs-dismiss="modal">Отмена</button>
            <button class="btn-save" data-bs-dismiss="modal" @click="updateCity">Сохранить</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.directory-page {
  display: grid;
  gap: 24px;
  padding: 8px 0 30px;
}

.page-header,
.custom-card,
.status-card {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 24px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 26px 28px;
}

.page-title {
  margin: 0 0 4px;
  color: #111827;
  font-size: 30px;
  font-weight: 900;
}

.page-subtitle {
  color: #6b7280;
  font-size: 15px;
  font-weight: 650;
}

.icon-btn,
.btn-action {
  width: 46px;
  height: 46px;
  border: 0;
  border-radius: 14px;
  display: inline-grid;
  place-items: center;
  background: #eef4ff;
  color: #0d6efd;
  transition: 0.18s ease;
}

.icon-btn:hover,
.btn-action:hover {
  transform: translateY(-1px);
}

.custom-card {
  padding: 24px;
}

.card-title-custom {
  color: #111827;
  font-size: 18px;
  font-weight: 900;
  margin-bottom: 18px;
}

.grid-forms {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
  gap: 24px;
}

.form-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px;
  gap: 12px;
}

.city-row {
  grid-template-columns: minmax(180px, 0.8fr) minmax(0, 1fr) 180px;
}

.custom-input {
  min-height: 46px;
  border: 1px solid #d9e1ec;
  border-radius: 14px;
  padding: 10px 14px;
  font-weight: 650;
  background: #fff;
  box-shadow: none !important;
}

.custom-input:focus {
  border-color: #0d6efd;
}

.btn-create,
.btn-save,
.btn-cancel {
  min-height: 46px;
  border: 0;
  border-radius: 14px;
  padding: 10px 18px;
  font-weight: 850;
}

.btn-create,
.btn-save {
  background: #1677ff;
  color: #fff;
}

.btn-create:disabled {
  opacity: 0.55;
}

.btn-cancel {
  background: #eef2f7;
  color: #374151;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  font-weight: 800;
}

.status-card.success {
  color: #087443;
  background: #effaf4;
}

.status-card.danger {
  color: #b42318;
  background: #fff1f0;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.counter {
  min-width: 42px;
  padding: 7px 12px;
  text-align: center;
  color: #0d6efd;
  background: #eef4ff;
  border-radius: 999px;
  font-weight: 900;
}

.empty-box {
  padding: 28px;
  text-align: center;
  color: #6b7280;
  background: #f8fafc;
  border-radius: 18px;
  font-weight: 750;
}

.items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.directory-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid #e5eaf2;
  border-radius: 18px;
}

.item-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.item-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #1677ff;
  background: #eef4ff;
}

.item-title {
  color: #111827;
  font-size: 16px;
  font-weight: 900;
}

.item-subtitle {
  color: #6b7280;
  font-size: 13px;
  font-weight: 700;
}

.item-actions,
.table-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-edit {
  background: #eef4ff;
  color: #0d6efd;
}

.btn-delete {
  background: #fff1f0;
  color: #dc3545;
}

.table-wrap {
  overflow-x: auto;
}

.directory-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 10px;
}

.directory-table th {
  padding: 0 16px 4px;
  color: #6b7280;
  font-size: 13px;
  font-weight: 900;
  text-transform: uppercase;
}

.directory-table td {
  padding: 16px;
  background: #f8fafc;
  border-top: 1px solid #e5eaf2;
  border-bottom: 1px solid #e5eaf2;
  font-weight: 750;
}

.directory-table td:first-child {
  border-left: 1px solid #e5eaf2;
  border-radius: 16px 0 0 16px;
}

.directory-table td:last-child {
  border-right: 1px solid #e5eaf2;
  border-radius: 0 16px 16px 0;
}

.custom-modal {
  border: 0;
  border-radius: 22px;
}

.modal-grid {
  display: grid;
  gap: 10px;
}

@media (max-width: 991px) {
  .grid-forms,
  .form-row,
  .city-row {
    grid-template-columns: 1fr;
  }

  .page-header {
    align-items: flex-start;
  }
}
</style>
