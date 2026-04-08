<script setup>
import axios from "axios";
import { ref, onBeforeMount, onMounted, onUnmounted, nextTick } from "vue";
import Cookies from "js-cookie";

const locations = ref([]);
const loading = ref(false);
const chats = ref([]);
const regions = ref([]);
const cities = ref([]);
const filteredRegions = ref([]);
const filteredCities = ref([]);
const filteredCitiesEdit = ref([]);

const locationToAdd = ref({
  name: "",
  lat: "",
  lon: "",
  synonyms: "",
  chats: [],
  region: "",
  city: "",
});

const locationToEdit = ref({});
const mapContainer = ref(null);
const mapState = ref({ map: null, marker: null });
const showAddMap = ref(false);
const editMapContainer = ref(null);
const editMapState = ref({ map: null, marker: null });
const previewMapContainer = ref(null);
const previewMapState = ref({ map: null, marker: null });
const locationToView = ref({ name: "", lat: null, lon: null });
let editModalEl = null;
let onEditModalShown = null;
let onEditModalHidden = null;
let previewModalEl = null;
let onPreviewModalShown = null;
let onPreviewModalHidden = null;
const DEFAULT_CENTER = [52.2896, 104.2806]; // Иркутск по умолчанию

function toFiniteCoord(value) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : NaN;
  }
  if (typeof value === "string") {
    const normalized = value.trim().replace(",", ".");
    const n = Number(normalized);
    return Number.isFinite(n) ? n : NaN;
  }
  return NaN;
}

function loadYandexMaps() {
  return new Promise((resolve, reject) => {
    if (window.ymaps) {
      window.ymaps.ready(() => resolve(window.ymaps));
      return;
    }
    const apiKey = import.meta.env.VITE_YANDEX_MAPS_API_KEY;
    if (!apiKey) {
      reject(new Error("VITE_YANDEX_MAPS_API_KEY is not set"));
      return;
    }
    const script = document.createElement("script");
    script.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`;
    script.async = true;
    script.onload = () => window.ymaps.ready(() => resolve(window.ymaps));
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

async function initMap() {
  if (!mapContainer.value) return;
  try {
    const ymaps = await loadYandexMaps();
    const map = new ymaps.Map(mapContainer.value, {
      center: DEFAULT_CENTER,
      zoom: 12,
      controls: ["zoomControl", "searchControl"],
    });
    let marker = null;

    map.events.add("click", (e) => {
      const coords = e.get("coords");
      if (marker) {
        marker.geometry.setCoordinates(coords);
      } else {
        marker = new ymaps.Placemark(coords, {}, { draggable: true });
        map.geoObjects.add(marker);
        marker.events.add("dragend", () => {
          const p = marker.geometry.getCoordinates();
          locationToAdd.value.lat = p[0].toFixed(6);
          locationToAdd.value.lon = p[1].toFixed(6);
        });
      }
      locationToAdd.value.lat = coords[0].toFixed(6);
      locationToAdd.value.lon = coords[1].toFixed(6);
    });

    mapState.value = { map, marker };
  } catch (e) {
    console.error("Failed to init Yandex Maps:", e);
  }
}

async function onShowAddMapClick() {
  if (showAddMap.value) return;
  showAddMap.value = true;
  await nextTick();
  await initMap();
  if (mapState.value.map) {
    setTimeout(() => mapState.value.map.container.fitToViewport(), 0);
  }
}

function onHideAddMapClick() {
  showAddMap.value = false;
  if (mapState.value.map) {
    mapState.value.map.destroy();
    mapState.value = { map: null, marker: null };
  }
}

function bindDraggableMarker(marker, target) {
  marker.events.add("dragend", () => {
    const p = marker.geometry.getCoordinates();
    target.value.lat = p[0].toFixed(6);
    target.value.lon = p[1].toFixed(6);
  });
}

function ensureEditMarker(coords) {
  const { map, marker } = editMapState.value;
  if (!map || !coords) return;
  if (!Array.isArray(coords) || coords.length !== 2) return;
  if (!Number.isFinite(coords[0]) || !Number.isFinite(coords[1])) return;

  if (marker) {
    marker.geometry.setCoordinates(coords);
    return;
  }

  const newMarker = new window.ymaps.Placemark(coords, {}, { draggable: true });
  map.geoObjects.add(newMarker);
  bindDraggableMarker(newMarker, locationToEdit);
  editMapState.value = { map, marker: newMarker };
}

function syncEditMapToForm() {
  const { map } = editMapState.value;
  if (!map) return;

  const lat = toFiniteCoord(locationToEdit.value.lat);
  const lon = toFiniteCoord(locationToEdit.value.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

  const coords = [lat, lon];
  ensureEditMarker(coords);
  map.setCenter(coords, 14);
}

async function initEditMap() {
  if (!editMapContainer.value) return;

  try {
    const ymaps = await loadYandexMaps();
    const map = new ymaps.Map(editMapContainer.value, {
      center: DEFAULT_CENTER,
      zoom: 12,
      controls: ["zoomControl"],
    });

    map.events.add("click", (e) => {
      const coords = e.get("coords");
      if (!Array.isArray(coords) || coords.length !== 2) return;
      if (!Number.isFinite(coords[0]) || !Number.isFinite(coords[1])) return;
      ensureEditMarker(coords);
      locationToEdit.value.lat = coords[0].toFixed(6);
      locationToEdit.value.lon = coords[1].toFixed(6);
    });

    editMapState.value = { map, marker: null };
  } catch (e) {
    console.error("Failed to init edit Yandex Map:", e);
  }
}

function destroyEditMap() {
  if (editMapState.value.map) {
    try {
      editMapState.value.map.destroy();
    } catch (e) {
      console.warn("Edit map destroy failed:", e);
    }
  }
  editMapState.value = { map: null, marker: null };
  if (editMapContainer.value) {
    editMapContainer.value.replaceChildren();
  }
}

function destroyPreviewMap() {
  if (previewMapState.value.map) {
    try {
      previewMapState.value.map.destroy();
    } catch (e) {
      console.warn("Preview map destroy failed:", e);
    }
  }
  previewMapState.value = { map: null, marker: null };
  if (previewMapContainer.value) {
    previewMapContainer.value.replaceChildren();
  }
}

async function initPreviewMap() {
  if (!previewMapContainer.value) return;

  try {
    const ymaps = await loadYandexMaps();
    const lat = Number(locationToView.value.lat);
    const lon = Number(locationToView.value.lon);
    const center = Number.isFinite(lat) && Number.isFinite(lon) ? [lat, lon] : DEFAULT_CENTER;
    const map = new ymaps.Map(previewMapContainer.value, {
      center,
      zoom: 15,
      controls: ["zoomControl"],
    });
    previewMapState.value = { map, marker: null };
  } catch (e) {
    console.error("Failed to init preview Yandex Map:", e);
  }
}

function syncPreviewMapToLocation() {
  const { map, marker } = previewMapState.value;
  const lat = Number(locationToView.value.lat);
  const lon = Number(locationToView.value.lon);
  if (!map || !Number.isFinite(lat) || !Number.isFinite(lon)) return;

  const coords = [lat, lon];
  if (marker) {
    marker.geometry.setCoordinates(coords);
  } else {
    const newMarker = new window.ymaps.Placemark(coords);
    map.geoObjects.add(newMarker);
    previewMapState.value = { map, marker: newMarker };
  }

  map.setCenter(coords, 15);
  setTimeout(() => map.container.fitToViewport(), 0);
}

async function fetchLocations() {
  loading.value = true;
  const r = await axios.get("/api/locations/");
  locations.value = r.data.features || []; // ожидаем GeoJSON
  loading.value = false;
}

async function fetchGeoRefs() {
  const [chatRes, rRes, cityRes] = await Promise.all([
    axios.get("/api/chats/"),
    axios.get("/api/regions/"),
    axios.get("/api/cities/")
  ]);
  chats.value = chatRes.data || [];
  regions.value = rRes.data || [];
  cities.value = cityRes.data || [];
  syncRegionCityOptions();
}

function syncRegionCityOptions() {
  filteredRegions.value = regions.value || [];
  if (locationToAdd.value.region) {
    filteredCities.value = cities.value.filter(
      c => c.region === parseInt(locationToAdd.value.region)
    );
  } else {
    filteredCities.value = [];
  }
}

function onAddRegionChange() {
  locationToAdd.value.city = "";
  syncRegionCityOptions();
}

async function onAddLocation() {
  if (!locationToAdd.value.lat || !locationToAdd.value.lon) {
    alert("Выберите точку на карте");
    return;
  }
  if (!locationToAdd.value.chats.length) {
    alert("Выберите хотя бы один чат");
    return;
  }
  await axios.post("/api/locations/", {
    geometry: {
      type: "Point",
      coordinates: [
        parseFloat(locationToAdd.value.lon),
        parseFloat(locationToAdd.value.lat)
      ]
    },
    properties: {
      name: locationToAdd.value.name,
      synonyms: locationToAdd.value.synonyms
        ? locationToAdd.value.synonyms.split(",").map(s => s.trim())
        : [],
      chats: locationToAdd.value.chats.map(id => parseInt(id)),
      city: locationToAdd.value.city ? parseInt(locationToAdd.value.city) : null,
    }
  });

  locationToAdd.value = { name: "", lat: "", lon: "", synonyms: "", chats: [], region: "", city: "" };
  await fetchLocations();
}

function onEditLocationClick(loc) {
  const regionId = loc.properties.region_id || "";
  const lat = toFiniteCoord(loc?.geometry?.coordinates?.[1]);
  const lon = toFiniteCoord(loc?.geometry?.coordinates?.[0]);
  locationToEdit.value = {
    id: loc.id,
    name: loc.properties.name,
    lat: Number.isFinite(lat) ? lat.toFixed(6) : "",
    lon: Number.isFinite(lon) ? lon.toFixed(6) : "",
    synonyms: loc.properties.synonyms.join(", "),
    chats: loc.properties.chats || (loc.properties.chat ? [loc.properties.chat] : []),
    region: regionId,
    city: loc.properties.city || "",
  };
  if (regionId) {
    filteredCitiesEdit.value = cities.value.filter(
      c => c.region === parseInt(regionId)
    );
  } else {
    filteredCitiesEdit.value = [];
  }

  syncEditMapToForm();
}

async function onUpdateLocationClick() {
  await axios.put(`/api/locations/${locationToEdit.value.id}/`, {
    geometry: {
      type: "Point",
      coordinates: [
        parseFloat(locationToEdit.value.lon),
        parseFloat(locationToEdit.value.lat)
      ]
    },
    properties: {
      name: locationToEdit.value.name,
      synonyms: locationToEdit.value.synonyms
        ? locationToEdit.value.synonyms.split(",").map(s => s.trim())
        : [],
      chats: (locationToEdit.value.chats || []).map(id => parseInt(id)),
      city: locationToEdit.value.city ? parseInt(locationToEdit.value.city) : null,
    }
  });

  await fetchLocations();
}

async function onRemoveLocation(loc) {
  await axios.delete(`/api/locations/${loc.id}/`);
  await fetchLocations();
}

function onViewLocationOnMap(loc) {
  const lat = toFiniteCoord(loc?.geometry?.coordinates?.[1]);
  const lon = toFiniteCoord(loc?.geometry?.coordinates?.[0]);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
  locationToView.value = {
    name: loc?.properties?.name || "Место",
    lat,
    lon,
  };
}

function openPreviewModal(loc) {
  onViewLocationOnMap(loc);
}

function openEditModal(loc) {
  onEditLocationClick(loc);
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await fetchGeoRefs();
  await fetchLocations();
});

onMounted(() => {
  editModalEl = document.getElementById("editLocationModal");
  previewModalEl = document.getElementById("viewLocationMapModal");
  onEditModalShown = async () => {
    destroyEditMap();
    await nextTick();
    await initEditMap();
    syncEditMapToForm();
    setTimeout(() => syncEditMapToForm(), 120);
    if (editMapState.value.map) {
      setTimeout(() => editMapState.value.map.container.fitToViewport(), 60);
    }
  };
  onEditModalHidden = () => {
    destroyEditMap();
  };
  onPreviewModalShown = async () => {
    destroyPreviewMap();
    await nextTick();
    await initPreviewMap();
    syncPreviewMapToLocation();
    setTimeout(() => syncPreviewMapToLocation(), 120);
  };
  onPreviewModalHidden = () => {
    destroyPreviewMap();
  };

  if (editModalEl) {
    editModalEl.addEventListener("shown.bs.modal", onEditModalShown);
    editModalEl.addEventListener("hidden.bs.modal", onEditModalHidden);
  }
  if (previewModalEl) {
    previewModalEl.addEventListener("shown.bs.modal", onPreviewModalShown);
    previewModalEl.addEventListener("hidden.bs.modal", onPreviewModalHidden);
  }
});

onUnmounted(() => {
  if (editModalEl && onEditModalShown) {
    editModalEl.removeEventListener("shown.bs.modal", onEditModalShown);
  }
  if (editModalEl && onEditModalHidden) {
    editModalEl.removeEventListener("hidden.bs.modal", onEditModalHidden);
  }
  if (previewModalEl && onPreviewModalShown) {
    previewModalEl.removeEventListener("shown.bs.modal", onPreviewModalShown);
  }
  if (previewModalEl && onPreviewModalHidden) {
    previewModalEl.removeEventListener("hidden.bs.modal", onPreviewModalHidden);
  }

  if (mapState.value.map) {
    mapState.value.map.destroy();
  }
  destroyEditMap();
  destroyPreviewMap();
});
</script>

<template>
  <div class="p-3">
    <h4>Словарь мест</h4>

    <!-- Добавление -->
    <div class="add-form-card mt-3">
      <form @submit.prevent="onAddLocation">
        <div class="row g-3">
          <div class="col-12 col-lg-4">
            <label class="form-label">Название</label>
            <input type="text" class="form-control" v-model="locationToAdd.name" required />
          </div>

          <div class="col-12 col-lg-4">
            <label class="form-label">Чаты</label>
            <div class="chat-checkboxes">
              <div class="form-check chat-check-item" v-for="c in chats" :key="c.id">
                <input
                  class="form-check-input"
                  type="checkbox"
                  :id="`add-chat-${c.id}`"
                  :value="c.id"
                  v-model="locationToAdd.chats"
                />
                <label class="form-check-label" :for="`add-chat-${c.id}`">{{ c.title }}</label>
              </div>
            </div>
            <small class="text-muted">Можно выбрать несколько</small>
          </div>

          <div class="col-6 col-md-3 col-lg-2">
            <label class="form-label">Область</label>
            <select class="form-select" v-model="locationToAdd.region" @change="onAddRegionChange" required>
              <option value="">—</option>
              <option v-for="r in filteredRegions" :key="r.id" :value="r.id">{{ r.name }}</option>
            </select>
          </div>

          <div class="col-6 col-md-3 col-lg-2">
            <label class="form-label">Город</label>
            <select class="form-select" v-model="locationToAdd.city" required>
              <option value="">—</option>
              <option v-for="c in filteredCities" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>

          <div class="col-6 col-md-3 col-lg-2">
            <label class="form-label">Широта (lat)</label>
            <input type="number" step="0.000001" class="form-control" v-model="locationToAdd.lat" readonly required />
          </div>

          <div class="col-6 col-md-3 col-lg-2">
            <label class="form-label">Долгота (lon)</label>
            <input type="number" step="0.000001" class="form-control" v-model="locationToAdd.lon" readonly required />
          </div>

          <div class="col-12 col-lg-8">
            <label class="form-label">Синонимы (через запятую)</label>
            <input type="text" class="form-control" v-model="locationToAdd.synonyms" />
          </div>

          <div class="col-12 col-lg-4 d-flex align-items-end">
            <button class="btn btn-primary w-100">Добавить</button>
          </div>
        </div>
      </form>
    </div>

    <div class="mt-3">
      <button
        v-if="!showAddMap"
        class="btn btn-outline-primary btn-sm mb-2"
        type="button"
        @click="onShowAddMapClick"
      >
        Показать карту
      </button>
      <button
        v-else
        class="btn btn-outline-secondary btn-sm mb-2"
        type="button"
        @click="onHideAddMapClick"
      >
        Скрыть карту
      </button>

      <div v-if="showAddMap">
      <div class="map-box" ref="mapContainer"></div>
      <small class="text-muted">Кликните по карте, чтобы выбрать точку.</small>
      </div>
    </div>

    <div v-if="loading" class="mt-3">Загрузка...</div>

    <!-- List -->
    <div v-else class="mt-3">
      <div v-for="loc in locations" :key="loc.id" class="item-box">

        <div>
          <strong>{{ loc.properties.name }}</strong>
          <br>
          <small class="text-muted">
            {{ (loc.properties.chat_titles || []).join(", ") || loc.properties.chat_title || "-" }} /
            {{ loc.properties.region_name || "-" }} /
            {{ loc.properties.city_name || "-" }}
          </small>
          <br>
          <small class="text-muted">
            Синонимы: 
            <span v-if="loc.properties.synonyms.length">{{ loc.properties.synonyms.join(", ") }}</span>
            <span v-else>-</span>
          </small>
        </div>

        <div class="item-actions">
          <button
            class="btn btn-outline-primary btn-sm"
            data-bs-toggle="modal"
            data-bs-target="#viewLocationMapModal"
            @click="openPreviewModal(loc)"
          >
            <i class="bi bi-geo-alt"></i> Посмотреть на карте
          </button>

          <button class="btn btn-warning btn-sm" data-bs-toggle="modal" data-bs-target="#editLocationModal" @click="openEditModal(loc)">
            <i class="bi bi-pen-fill"></i>
          </button>

          <button class="btn btn-danger btn-sm" @click="onRemoveLocation(loc)">
            <i class="bi bi-trash3-fill"></i>
          </button>
        </div>

      </div>
    </div>

    <!-- View map modal -->
    <div class="modal fade" id="viewLocationMapModal" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ locationToView.name || "Место на карте" }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="map-box map-box-preview" ref="previewMapContainer"></div>
            <small class="text-muted">
              lat: {{ locationToView.lat }}, lon: {{ locationToView.lon }}
            </small>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Закрыть</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <div class="modal fade" id="editLocationModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">

          <div class="modal-header">
            <h5 class="modal-title">Редактировать место</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>

          <div class="modal-body">
            <div class="form-floating mb-2">
              <input type="text" class="form-control" v-model="locationToEdit.name" />
              <label>Название</label>
            </div>

            <div class="mb-2">
              <label class="form-label mb-1">Чаты</label>
              <div class="chat-checkboxes">
                <div class="form-check chat-check-item" v-for="c in chats" :key="c.id">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    :id="`edit-chat-${c.id}`"
                    :value="c.id"
                    v-model="locationToEdit.chats"
                  />
                  <label class="form-check-label" :for="`edit-chat-${c.id}`">{{ c.title }}</label>
                </div>
              </div>
              <small class="text-muted">Можно выбрать несколько</small>
            </div>

            <div class="form-floating mb-2">
              <select class="form-select" v-model="locationToEdit.region" disabled>
                <option value="">—</option>
                <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
              </select>
              <label>Область</label>
            </div>

            <div class="form-floating mb-2">
              <select class="form-select" v-model="locationToEdit.city">
                <option value="">—</option>
                <option v-for="c in filteredCitiesEdit" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
              <label>Город</label>
            </div>

            <div class="form-floating mb-2">
              <input type="number" step="0.000001" class="form-control" v-model="locationToEdit.lat" />
              <label>Широта (lat)</label>
            </div>

            <div class="form-floating mb-2">
              <input type="number" step="0.000001" class="form-control" v-model="locationToEdit.lon" />
              <label>Долгота (lon)</label>
            </div>

            <div class="mt-3">
              <div class="map-box map-box-edit" ref="editMapContainer"></div>
              <small class="text-muted">Кликните по карте или перетащите маркер, чтобы изменить координаты.</small>
            </div>

            <div class="form-floating">
              <input type="text" class="form-control" v-model="locationToEdit.synonyms" />
              <label>Синонимы</label>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
            <button class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateLocationClick">
              Сохранить
            </button>
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
  padding: .5rem;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  margin-bottom: .5rem;
}
.item-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: .5rem;
}
.map-box {
  width: 100%;
  height: 320px;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
}

.map-box-edit {
  height: 240px;
}

.map-box-preview {
  height: 420px;
}

.chat-checkboxes {
  max-height: 132px;
  overflow: auto;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  padding: 0.55rem 0.65rem;
  background: #fff;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.4rem 0.75rem;
}

.chat-check-item {
  display: flex;
  align-items: center;
  min-width: 0;
}

.chat-check-item .form-check-input {
  margin-top: 0;
  margin-right: 0.45rem;
  flex-shrink: 0;
}

.chat-check-item .form-check-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
