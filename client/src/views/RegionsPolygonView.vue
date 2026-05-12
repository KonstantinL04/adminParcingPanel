<script setup>
import { nextTick, onBeforeMount, onMounted, onUnmounted, ref } from "vue";
import axios from "axios";
import Cookies from "js-cookie";

const file = ref(null);
const isUploading = ref(false);
const isLoading = ref(false);
const message = ref("");
const error = ref("");
const regions = ref([]);

const regionToEdit = ref({ id: null, name: "" });
const regionToView = ref({ id: null, name: "", boundary_geojson: null });
const previewMapContainer = ref(null);
const previewMapState = ref({ map: null, geoJsonLayer: null });

const DEFAULT_CENTER = [52.2896, 104.2806]; // Иркутск
let previewModalEl = null;
let onPreviewModalShown = null;
let onPreviewModalHidden = null;
let previewModalGeneration = 0;

function onFileChange(event) {
  file.value = event.target.files?.[0] || null;
}

function clearStatus() {
  message.value = "";
  error.value = "";
}

async function loadRegions() {
  isLoading.value = true;
  clearStatus();
  try {
    const { data } = await axios.get("/api/regions/");
    const list = Array.isArray(data) ? data : [];
    regions.value = [...list].sort((a, b) => {
      const nameA = String(a?.name || "").toLowerCase();
      const nameB = String(b?.name || "").toLowerCase();
      return nameA.localeCompare(nameB, "ru");
    });
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось загрузить список областей.";
  } finally {
    isLoading.value = false;
  }
}

async function uploadGeojson() {
  if (!file.value) {
    error.value = "Выберите GeoJSON файл с областями.";
    return;
  }

  isUploading.value = true;
  clearStatus();

  try {
    const fd = new FormData();
    fd.append("file", file.value);

    const { data } = await axios.post("/api/regions/upload_geojson/", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    message.value = `Готово: создано ${data.created}, обновлено ${data.updated}, пропущено ${data.skipped}`;
    file.value = null;
    const input = document.getElementById("regions-geojson-input");
    if (input) input.value = "";
    await loadRegions();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Ошибка загрузки GeoJSON областей.";
  } finally {
    isUploading.value = false;
  }
}

function onEditRegionClick(region) {
  regionToEdit.value = {
    id: region.id,
    name: region.name || "",
  };
}

async function onUpdateRegionClick() {
  const name = String(regionToEdit.value.name || "").trim();
  if (!name) return;

  try {
    await axios.patch(`/api/regions/${regionToEdit.value.id}/`, { name });
    await loadRegions();
  } catch (e) {
    alert(e?.response?.data?.detail || "Не удалось сохранить изменения области.");
  }
}

async function onRemoveRegion(region) {
  if (!confirm(`Удалить область «${region.name}»?`)) return;
  try {
    await axios.delete(`/api/regions/${region.id}/`);
    await loadRegions();
  } catch (e) {
    alert(e?.response?.data?.detail || "Не удалось удалить область.");
  }
}

async function openPreviewModal(region) {
  regionToView.value = {
    id: region.id,
    name: region.name || "Область",
    boundary_geojson: region.boundary_geojson || null,
  };
  try {
    const { data } = await axios.get(`/api/regions/${region.id}/`);
    regionToView.value = {
      id: data.id,
      name: data.name || region.name || "Область",
      boundary_geojson: data.boundary_geojson || region.boundary_geojson || null,
    };
  } catch (e) {
    console.warn("Не удалось получить полигон области:", e);
  }
}

function loadLeaflet() {
  return new Promise((resolve, reject) => {
    if (window.L) {
      resolve(window.L);
      return;
    }

    if (!document.querySelector('link[data-leaflet-css="true"]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      link.setAttribute("data-leaflet-css", "true");
      document.head.appendChild(link);
    }

    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.async = true;
    script.onload = () => resolve(window.L);
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

async function initPreviewMap() {
  if (!previewMapContainer.value) return;

  try {
    const L = await loadLeaflet();
    const map = L.map(previewMapContainer.value, {
      center: DEFAULT_CENTER,
      zoom: 6,
      zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);

    previewMapState.value = { map, geoJsonLayer: null };
    setTimeout(() => map.invalidateSize(), 0);
  } catch (e) {
    console.error("Failed to init OSM preview map:", e);
  }
}

function destroyPreviewMap() {
  if (previewMapState.value.map) {
    try {
      previewMapState.value.map.remove();
    } catch (e) {
      console.warn("Preview map destroy failed:", e);
    }
  }
  previewMapState.value = { map: null, geoJsonLayer: null };
  if (previewMapContainer.value) {
    previewMapContainer.value.replaceChildren();
  }
}

function syncPreviewMapToRegion() {
  const { map, geoJsonLayer } = previewMapState.value;
  if (!map) return;

  if (geoJsonLayer) {
    map.removeLayer(geoJsonLayer);
    previewMapState.value.geoJsonLayer = null;
  }

  if (!regionToView.value.boundary_geojson) {
    map.setView(DEFAULT_CENTER, 6);
    return;
  }

  try {
    const L = window.L;
    const feature = {
      type: "Feature",
      properties: {},
      geometry: regionToView.value.boundary_geojson,
    };

    const layer = L.geoJSON(feature, {
      style: {
        color: "#1976d2",
        weight: 2,
        fillColor: "#1e88e5",
        fillOpacity: 0.22,
      },
    }).addTo(map);

    previewMapState.value.geoJsonLayer = layer;

    const bounds = layer.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [24, 24] });
      return;
    }
  } catch (e) {
    console.error("Не удалось отрисовать полигон области в OSM:", e);
  }

  map.setView(DEFAULT_CENTER, 6);
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await loadRegions();
});

onMounted(() => {
  previewModalEl = document.getElementById("viewRegionMapModal");

  onPreviewModalShown = async () => {
    previewModalGeneration += 1;
    const currentGeneration = previewModalGeneration;
    destroyPreviewMap();
    await nextTick();
    if (currentGeneration !== previewModalGeneration) return;
    await initPreviewMap();
    if (currentGeneration !== previewModalGeneration) return;
    syncPreviewMapToRegion();
    setTimeout(() => syncPreviewMapToRegion(), 120);
  };

  onPreviewModalHidden = () => {
    const hiddenGeneration = previewModalGeneration;
    setTimeout(() => {
      if (hiddenGeneration === previewModalGeneration) {
        destroyPreviewMap();
      }
    }, 0);
  };

  if (previewModalEl) {
    previewModalEl.addEventListener("shown.bs.modal", onPreviewModalShown);
    previewModalEl.addEventListener("hidden.bs.modal", onPreviewModalHidden);
  }
});

onUnmounted(() => {
  if (previewModalEl && onPreviewModalShown) {
    previewModalEl.removeEventListener("shown.bs.modal", onPreviewModalShown);
  }
  if (previewModalEl && onPreviewModalHidden) {
    previewModalEl.removeEventListener("hidden.bs.modal", onPreviewModalHidden);
  }
  destroyPreviewMap();
});
</script>

<template>
  <div class="page-wrap">

    <!-- HEADER -->
    <div class="page-header mb-4">
      <div>
        <h2 class="page-title">
          <i class="bi bi-bounding-box me-2"></i>
          Полигоны областей
        </h2>
        <div class="page-subtitle">
          Управление географическими областями и их границами
        </div>
      </div>
    </div>

    <!-- UPLOAD CARD -->
    <div class="custom-card mb-4">
      <div class="card-title-custom">
        <i class="bi bi-cloud-upload-fill me-2"></i>
        Загрузка GeoJSON
      </div>

      <div class="row g-3 align-items-end">
        <div class="col-lg-9">
          <label class="form-label">GeoJSON областей</label>
          <div class="file-upload-wrapper">
            <input
              id="regions-geojson-input"
              class="form-control custom-input file-input-hidden"
              type="file"
              accept=".geojson,.json,application/geo+json,application/json"
              @change="onFileChange"
            />
            <label for="regions-geojson-input" class="file-upload-label">
              <i class="bi bi-file-earmark-code me-2"></i>
              <span v-if="file">{{ file.name }}</span>
              <span v-else class="text-muted">Выберите файл .geojson или .json</span>
            </label>
          </div>
          <div class="info-text mt-2">
            <i class="bi bi-info-circle me-1"></i>
            Поддерживаются <code>FeatureCollection</code> и формат
            <code>{"Область":{"0":[[lat, lon], ...]}}</code>
          </div>
        </div>
        <div class="col-lg-3">
          <button class="btn-create w-100" :disabled="isUploading || !file" @click="uploadGeojson">
            <span v-if="isUploading" class="spinner-border spinner-border-sm me-2"></span>
            <i class="bi bi-cloud-arrow-up-fill me-2"></i>
            Загрузить области
          </button>
        </div>
      </div>
    </div>

    <!-- SUCCESS MESSAGE -->
    <div v-if="message" class="success-card mb-4">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-check-circle-fill"></i>
        <span>{{ message }}</span>
      </div>
    </div>

    <!-- ERROR MESSAGE -->
    <div v-if="error" class="error-card mb-4">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-exclamation-triangle-fill"></i>
        <span>{{ error }}</span>
      </div>
    </div>

    <!-- LIST CARD -->
    <div class="custom-card">
      <div class="card-title-custom mb-4">
        <i class="bi bi-list-ul me-2"></i>
        Список областей
      </div>

      <div
        v-if="isLoading"
        class="loading-box"
      >
        Загрузка...
      </div>

      <div
        v-else-if="regions.length === 0"
        class="empty-box"
      >
        <i class="bi bi-inbox me-2"></i>
        Областей пока нет
      </div>

      <div
        v-else
        class="regions-grid"
      >
        <div
          v-for="region in regions"
          :key="region.id"
          class="region-card"
        >
          <div class="region-left">
            <div class="region-icon">
              <i class="bi bi-hexagon-fill"></i>
            </div>
            <div class="region-info">
              <div class="region-name">
                {{ region.name }}
              </div>
              <div class="region-polygon-status">
                Полигон:
                <span class="polygon-badge" :class="region.has_boundary ? 'has-polygon' : 'no-polygon'">
                  {{ region.has_boundary ? "есть" : "нет" }}
                </span>
              </div>
            </div>
          </div>

          <div class="item-actions">
            <button
              class="btn-action btn-map"
              data-bs-toggle="modal"
              data-bs-target="#viewRegionMapModal"
              @click="openPreviewModal(region)"
              :disabled="!region.has_boundary"
            >
              <i class="bi bi-geo-alt me-1"></i>
              На карте
            </button>

            <button
              class="btn-action btn-edit"
              data-bs-toggle="modal"
              data-bs-target="#editRegionModal"
              @click="onEditRegionClick(region)"
            >
              <i class="bi bi-pencil-square me-1"></i>
              Ред.
            </button>

            <button
              class="btn-action btn-delete"
              @click="onRemoveRegion(region)"
            >
              <i class="bi bi-trash3 me-1"></i>
              Удалить
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- EDIT MODAL -->
    <div class="modal fade" id="editRegionModal" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content custom-modal">
          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title fw-bold">Редактировать область</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <label class="form-label">Название области</label>
            <input
              type="text"
              class="form-control custom-input"
              v-model="regionToEdit.name"
              placeholder="Введите название"
            />
          </div>
          <div class="modal-footer border-0 pt-0">
            <button class="btn-cancel" data-bs-dismiss="modal">Отмена</button>
            <button class="btn-save" data-bs-dismiss="modal" @click="onUpdateRegionClick">
              Сохранить
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- VIEW MAP MODAL -->
    <div class="modal fade" id="viewRegionMapModal" tabindex="-1">
      <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content custom-modal">
          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title fw-bold">{{ regionToView.name || "Полигон области" }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="map-box map-box-preview" ref="previewMapContainer"></div>
          </div>
          <div class="modal-footer border-0 pt-0">
            <button class="btn-cancel" data-bs-dismiss="modal">Закрыть</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* Общие стили */
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
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(15,23,42,0.06);
  border: 1px solid rgba(0,0,0,0.04);
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
}

.btn-create:hover:not(:disabled) {
  background: #0b5ed7;
  transform: translateY(-1px);
}

.btn-create:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-action {
  border: 0;
  border-radius: 14px;
  padding: 10px 14px;
  font-weight: 700;
  transition: 0.2s ease;
  white-space: nowrap;
}

.btn-edit {
  background: rgba(13,110,253,0.1);
  color: #0d6efd;
}

.btn-edit:hover {
  background: #0d6efd;
  color: #fff;
}

.btn-delete {
  background: rgba(220,53,69,0.1);
  color: #dc3545;
}

.btn-delete:hover {
  background: #dc3545;
  color: #fff;
}

.btn-map {
  background: rgba(25,135,84,0.1);
  color: #198754;
}

.btn-map:hover {
  background: #198754;
  color: #fff;
}

.btn-map:disabled {
  background: #e9ecef;
  color: #adb5bd;
  cursor: not-allowed;
  opacity: 1;
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

/* Info text */
.info-text {
  color: #6c757d;
  font-size: 13px;
  font-weight: 500;
}

.info-text code {
  background: #f0f2f5;
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 12px;
  color: #0d6efd;
}

/* Success/Error cards */
.success-card {
  background: rgba(25,135,84,0.08);
  border: 1px solid rgba(25,135,84,0.2);
  border-radius: 16px;
  padding: 14px 18px;
  color: #198754;
  font-weight: 600;
  font-size: 14px;
}

.error-card {
  background: rgba(220,53,69,0.08);
  border: 1px solid rgba(220,53,69,0.2);
  border-radius: 16px;
  padding: 14px 18px;
  color: #dc3545;
  font-weight: 600;
  font-size: 14px;
}

/* Regions grid */
.regions-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.region-card {
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

.region-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15,23,42,0.06);
}

.region-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 0;
}

.region-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: rgba(111,66,193,0.1);
  color: #6f42c1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.region-info {
  min-width: 0;
  flex: 1;
}

.region-name {
  font-size: 16px;
  font-weight: 700;
  color: #111;
  margin-bottom: 4px;
  word-break: break-word;
}

.region-polygon-status {
  font-size: 13px;
  color: #6c757d;
}

.polygon-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 8px;
  font-weight: 700;
  font-size: 12px;
  margin-left: 6px;
}

.polygon-badge.has-polygon {
  background: rgba(25,135,84,0.1);
  color: #198754;
}

.polygon-badge.no-polygon {
  background: rgba(108,117,125,0.1);
  color: #6c757d;
}

.item-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

/* Map */
.map-box {
  width: 100%;
  height: 320px;
  border: 1px solid #eef1f4;
  border-radius: 20px;
  overflow: hidden;
}

.map-box-preview {
  height: 480px;
}

/* States */
.loading-box,
.empty-box {
  padding: 40px;
  text-align: center;
  color: #6c757d;
  font-weight: 600;
}

/* Modals */
.custom-modal {
  border: 0;
  border-radius: 24px;
  padding: 10px;
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

/* Адаптив */
@media (max-width: 991.98px) {
  .custom-card {
    padding: 18px;
    border-radius: 20px;
  }

  .page-title {
    font-size: 22px;
  }

  .region-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .item-actions {
    width: 100%;
    flex-direction: column;
  }

  .btn-action,
  .btn-create {
    width: 100%;
    justify-content: center;
  }
}
</style>