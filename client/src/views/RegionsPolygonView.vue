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
  <div class="p-3">
    <h4>Полигоны областей</h4>

    <div class="add-form-card mt-3">
      <div class="row g-3 align-items-end">
        <div class="col-md-9">
          <label class="form-label">GeoJSON областей</label>
          <input
            id="regions-geojson-input"
            class="form-control"
            type="file"
            accept=".geojson,.json,application/geo+json,application/json"
            @change="onFileChange"
          />
          <div class="form-text">
            Поддерживаются <code>FeatureCollection</code> и формат
            <code>&lbrace;"Область":&lbrace;"0":[[lat, lon], ...]&rbrace;&rbrace;</code>.
          </div>
        </div>
        <div class="col-md-3 d-grid">
          <button class="btn btn-primary" :disabled="isUploading || !file" @click="uploadGeojson">
            <span v-if="isUploading" class="spinner-border spinner-border-sm me-2"></span>
            Загрузить области
          </button>
        </div>
      </div>
    </div>

    <div class="alert alert-success mt-3 mb-0" v-if="message">{{ message }}</div>
    <div class="alert alert-danger mt-3 mb-0" v-if="error">{{ error }}</div>

    <div v-if="isLoading" class="mt-3">Загрузка...</div>

    <div v-else class="mt-3">
      <div v-for="region in regions" :key="region.id" class="item-box">
        <div>
          <strong>{{ region.name }}</strong>
          <br />
          <small class="text-muted">
            Полигон:
            <span class="badge" :class="region.has_boundary ? 'text-bg-success' : 'text-bg-secondary'">
              {{ region.has_boundary ? "есть" : "нет" }}
            </span>
          </small>
        </div>

        <div class="item-actions">
          <button
            class="btn btn-outline-primary btn-sm"
            data-bs-toggle="modal"
            data-bs-target="#viewRegionMapModal"
            @click="openPreviewModal(region)"
            :disabled="!region.has_boundary"
          >
            <i class="bi bi-geo-alt"></i> Посмотреть на карте
          </button>

          <button
            class="btn btn-warning btn-sm"
            data-bs-toggle="modal"
            data-bs-target="#editRegionModal"
            @click="onEditRegionClick(region)"
          >
            <i class="bi bi-pen-fill"></i>
          </button>

          <button class="btn btn-danger btn-sm" @click="onRemoveRegion(region)">
            <i class="bi bi-trash3-fill"></i>
          </button>
        </div>
      </div>

      <div v-if="regions.length === 0" class="text-muted">Областей пока нет.</div>
    </div>

    <div class="modal fade" id="editRegionModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Редактировать область</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>

          <div class="modal-body">
            <div class="form-floating">
              <input type="text" class="form-control" v-model="regionToEdit.name" />
              <label>Название области</label>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Отмена</button>
            <button class="btn btn-primary btn-sm" data-bs-dismiss="modal" @click="onUpdateRegionClick">
              Сохранить
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" id="viewRegionMapModal" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ regionToView.name || "Полигон области" }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="map-box map-box-preview" ref="previewMapContainer"></div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Закрыть</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.add-form-card {
  border: 1px solid #d0d0d0;
  border-radius: 10px;
  background: #fff;
  padding: 1rem;
}

.item-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 0.75rem;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  margin-bottom: 0.5rem;
  background: #fff;
}

.item-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.map-box {
  width: 100%;
  height: 320px;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
}

.map-box-preview {
  height: 480px;
}
</style>
