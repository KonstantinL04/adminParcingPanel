<script setup>
import axios from "axios";
import { computed, ref, onBeforeMount, onMounted, onUnmounted, nextTick } from "vue";
import Cookies from "js-cookie";

const locations = ref([]);
const loading = ref(false);
const chats = ref([]);
const locationChatFilters = ref([]);
const appliedLocationChatFilters = ref([]);

const locationToAdd = ref({
  name: "",
  lat: "",
  lon: "",
  synonyms: "",
  chats: [],
});

const locationToEdit = ref({});
const mapContainer = ref(null);
const mapState = ref({ map: null, marker: null });
const showAddMap = ref(false);
const editMapContainer = ref(null);
const editMapState = ref({ map: null, marker: null });
const editMapKey = ref(0);
const previewMapContainer = ref(null);
const previewMapState = ref({ map: null, marker: null });
const locationToView = ref({ name: "", lat: null, lon: null });
let editModalEl = null;
let onEditModalShown = null;
let onEditModalHidden = null;
let previewModalEl = null;
let onPreviewModalShown = null;
let onPreviewModalHidden = null;
let editModalGeneration = 0;
let previewModalGeneration = 0;
const DEFAULT_CENTER = [52.2896, 104.2806];

// Dropdown states
const showAddChatDropdown = ref(false);
const showEditChatDropdown = ref(false);
const showFilterChatDropdown = ref(false);

// Dropdown refs
const addChatDropdown = ref(null);
const editChatDropdown = ref(null);
const filterChatDropdown = ref(null);

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

function hasValidLatLon(lat, lon) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
  if (Math.abs(lat) < 0.000001 && Math.abs(lon) < 0.000001) return false;
  return true;
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

  if (!marker) return;
  marker.geometry.setCoordinates(coords);
}

function syncEditMapToForm() {
  const { map } = editMapState.value;
  if (!map) return;

  const lat = toFiniteCoord(locationToEdit.value.lat);
  const lon = toFiniteCoord(locationToEdit.value.lon);
  if (!hasValidLatLon(lat, lon)) {
    if (editMapState.value.marker) {
      editMapState.value.marker.geometry.setCoordinates(DEFAULT_CENTER);
    }
    map.setCenter(DEFAULT_CENTER, 12);
    return;
  }

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

    const marker = new ymaps.Placemark(
      DEFAULT_CENTER,
      {},
      {
        draggable: true,
        preset: "islands#blueIcon",
      }
    );
    map.geoObjects.add(marker);
    bindDraggableMarker(marker, locationToEdit);

    map.events.add("click", (e) => {
      const coords = e.get("coords");
      if (!Array.isArray(coords) || coords.length !== 2) return;
      if (!Number.isFinite(coords[0]) || !Number.isFinite(coords[1])) return;
      ensureEditMarker(coords);
      locationToEdit.value.lat = coords[0].toFixed(6);
      locationToEdit.value.lon = coords[1].toFixed(6);
    });

    editMapState.value = { map, marker };
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
    const center = hasValidLatLon(lat, lon) ? [lat, lon] : DEFAULT_CENTER;
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
  if (!map || !hasValidLatLon(lat, lon)) {
    if (map) map.setCenter(DEFAULT_CENTER, 12);
    return;
  }

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
  locations.value = r.data.features || [];
  loading.value = false;
}

function getLocationChatIds(loc) {
  const ids = [];
  const chat = Number(loc?.properties?.chat);
  if (Number.isFinite(chat)) ids.push(chat);
  const extra = Array.isArray(loc?.properties?.chats) ? loc.properties.chats : [];
  for (const id of extra) {
    const n = Number(id);
    if (Number.isFinite(n)) ids.push(n);
  }
  return [...new Set(ids)];
}

function hasCoordinates(loc) {
  const lat = toFiniteCoord(loc?.geometry?.coordinates?.[1]);
  const lon = toFiniteCoord(loc?.geometry?.coordinates?.[0]);
  return hasValidLatLon(lat, lon);
}

const visibleLocations = computed(() => {
  const selected = new Set((appliedLocationChatFilters.value || []).map((id) => Number(id)));
  const byChat = (locations.value || []).filter((loc) => {
    if (!selected.size) return true;
    const ids = getLocationChatIds(loc);
    return ids.some((id) => selected.has(id));
  });

  return [...byChat].sort((a, b) => {
    const aTime = Date.parse(a?.properties?.created_at || "");
    const bTime = Date.parse(b?.properties?.created_at || "");
    if (Number.isFinite(aTime) && Number.isFinite(bTime) && aTime !== bTime) {
      return bTime - aTime;
    }
    return Number(b?.id || 0) - Number(a?.id || 0);
  });
});

function applyLocationFilters() {
  appliedLocationChatFilters.value = [...locationChatFilters.value];
}

function applyLocationFiltersAndClose() {
  applyLocationFilters();
  const modalEl = document.getElementById("locationFilterModal");
  if (modalEl) {
    const bsModal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    bsModal.hide();
  }
}

function resetLocationFilters() {
  locationChatFilters.value = [];
  appliedLocationChatFilters.value = [];
}

async function fetchGeoRefs() {
  const [chatRes] = await Promise.all([axios.get("/api/chats/")]);
  chats.value = chatRes.data || [];
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
    }
  });

  locationToAdd.value = { name: "", lat: "", lon: "", synonyms: "", chats: [] };
  await fetchLocations();
}

function onEditLocationClick(loc) {
  const lat = toFiniteCoord(loc?.geometry?.coordinates?.[1]);
  const lon = toFiniteCoord(loc?.geometry?.coordinates?.[0]);
  const hasCoords = hasValidLatLon(lat, lon);
  locationToEdit.value = {
    id: loc.id,
    name: loc.properties.name,
    lat: hasCoords ? lat.toFixed(6) : "",
    lon: hasCoords ? lon.toFixed(6) : "",
    synonyms: loc.properties.synonyms.join(", "),
    chats: loc.properties.chats || (loc.properties.chat ? [loc.properties.chat] : []),
  };

  syncEditMapToForm();
}

async function onUpdateLocationClick() {
  const lat = toFiniteCoord(locationToEdit.value.lat);
  const lon = toFiniteCoord(locationToEdit.value.lon);
  const geometry = hasValidLatLon(lat, lon)
    ? {
        type: "Point",
        coordinates: [lon, lat],
      }
    : null;

  await axios.put(`/api/locations/${locationToEdit.value.id}/`, {
    geometry,
    properties: {
      name: locationToEdit.value.name,
      synonyms: locationToEdit.value.synonyms
        ? locationToEdit.value.synonyms.split(",").map(s => s.trim())
        : [],
      chats: (locationToEdit.value.chats || []).map(id => parseInt(id)),
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
  if (!hasValidLatLon(lat, lon)) return;
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

// Dropdown methods
function toggleAddChatDropdown() {
  showAddChatDropdown.value = !showAddChatDropdown.value;
}

function toggleEditChatDropdown() {
  showEditChatDropdown.value = !showEditChatDropdown.value;
}

function toggleFilterChatDropdown() {
  showFilterChatDropdown.value = !showFilterChatDropdown.value;
}

function selectAllAddChats() {
  locationToAdd.value.chats = chats.value.map(c => c.id);
}

function selectAllEditChats() {
  locationToEdit.value.chats = chats.value.map(c => c.id);
}

function selectAllFilterChats() {
  locationChatFilters.value = chats.value.map(c => c.id);
}

function handleClickOutside(event) {
  if (addChatDropdown.value && !addChatDropdown.value.contains(event.target)) {
    showAddChatDropdown.value = false;
  }
  if (editChatDropdown.value && !editChatDropdown.value.contains(event.target)) {
    showEditChatDropdown.value = false;
  }
  if (filterChatDropdown.value && !filterChatDropdown.value.contains(event.target)) {
    showFilterChatDropdown.value = false;
  }
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await fetchGeoRefs();
  await fetchLocations();
});

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
  
  editModalEl = document.getElementById("editLocationModal");
  previewModalEl = document.getElementById("viewLocationMapModal");
  onEditModalShown = async () => {
    editModalGeneration += 1;
    const currentGeneration = editModalGeneration;
    editMapKey.value += 1;
    await nextTick();
    if (currentGeneration !== editModalGeneration) return;
    destroyEditMap();
    await initEditMap();
    if (currentGeneration !== editModalGeneration) return;
    syncEditMapToForm();
    if (editMapState.value.map) {
      editMapState.value.map.container.fitToViewport();
    }
  };
  onEditModalHidden = () => {
    editModalGeneration += 1;
    destroyEditMap();
  };
  onPreviewModalShown = async () => {
    previewModalGeneration += 1;
    const currentGeneration = previewModalGeneration;
    destroyPreviewMap();
    await nextTick();
    if (currentGeneration !== previewModalGeneration) return;
    await initPreviewMap();
    if (currentGeneration !== previewModalGeneration) return;
    syncPreviewMapToLocation();
    setTimeout(() => syncPreviewMapToLocation(), 120);
  };
  onPreviewModalHidden = () => {
    const hiddenGeneration = previewModalGeneration;
    setTimeout(() => {
      if (hiddenGeneration === previewModalGeneration) {
        destroyPreviewMap();
      }
    }, 0);
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
  document.removeEventListener('click', handleClickOutside);
  
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
  <div class="page-wrap">

    <!-- HEADER -->
    <div class="page-header mb-4">
      <div>
        <h2 class="page-title">
          <i class="bi bi-geo-alt-fill me-2"></i>
          Словарь мест
        </h2>
        <div class="page-subtitle">
          Управление геолокациями для парсинга
        </div>
      </div>
    </div>

    <!-- ADD LOCATION -->
    <div class="custom-card mb-4">
      <div class="card-title-custom">
        <i class="bi bi-plus-circle-fill me-2"></i>
        Добавить место
      </div>

      <form @submit.prevent="onAddLocation">
        <div class="row g-3 align-items-end">
          <div class="col-lg-4">
            <label class="form-label">Название</label>
            <input
              type="text"
              class="form-control custom-input"
              v-model="locationToAdd.name"
              required
              placeholder="Название места"
            />
          </div>

          <div class="col-lg-4">
            <label class="form-label">Чаты</label>
            <div class="main-dropdown" ref="addChatDropdown">
              <button
                class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
                type="button"
                @click="toggleAddChatDropdown"
              >
                <span v-if="locationToAdd.chats.length === 0" class="text-muted">Выберите чаты</span>
                <span v-else class="selected-count">Выбрано: {{ locationToAdd.chats.length }}</span>
                <i class="bi bi-chevron-down ms-2"></i>
              </button>
              <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: showAddChatDropdown }">
                <div class="dropdown-header-actions">
                  <button
                    type="button"
                    class="dropdown-action-btn"
                    @click="selectAllAddChats"
                  >
                    <i class="bi bi-check-all me-1"></i>
                    Выбрать все
                  </button>
                  <button
                    type="button"
                    class="dropdown-action-btn danger"
                    @click="locationToAdd.chats = []"
                    v-if="locationToAdd.chats.length > 0"
                  >
                    <i class="bi bi-x-lg me-1"></i>
                    Сбросить
                  </button>
                </div>
                <div class="dropdown-items-scroll">
                  <label
                    v-for="c in chats"
                    :key="c.id"
                    class="dropdown-item-custom"
                    :class="{ active: locationToAdd.chats.includes(c.id) }"
                  >
                    <input
                      type="checkbox"
                      :value="c.id"
                      v-model="locationToAdd.chats"
                      class="form-check-input me-2"
                    />
                    <span>{{ c.title }}</span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <div class="col-md-3 col-lg-2">
            <label class="form-label">Широта (lat)</label>
            <input
              type="number"
              step="0.000001"
              class="form-control custom-input"
              v-model="locationToAdd.lat"
              readonly
              required
              placeholder="lat"
            />
          </div>

          <div class="col-md-3 col-lg-2">
            <label class="form-label">Долгота (lon)</label>
            <input
              type="number"
              step="0.000001"
              class="form-control custom-input"
              v-model="locationToAdd.lon"
              readonly
              required
              placeholder="lon"
            />
          </div>

          <div class="col-lg-8">
            <label class="form-label">Синонимы (через запятую)</label>
            <input
              type="text"
              class="form-control custom-input"
              v-model="locationToAdd.synonyms"
              placeholder="@username, название"
            />
          </div>

          <div class="col-lg-4 d-flex align-items-end gap-2">
            <button class="btn-create flex-grow-1">
              <i class="bi bi-plus-lg me-2"></i>
              Добавить
            </button>
          </div>
        </div>
      </form>

      <!-- Map toggle -->
      <div class="mt-3">
        <button
          v-if="!showAddMap"
          class="btn-map-toggle"
          type="button"
          @click="onShowAddMapClick"
        >
          <i class="bi bi-map me-2"></i>
          Показать карту
        </button>
        <button
          v-else
          class="btn-map-toggle"
          type="button"
          @click="onHideAddMapClick"
        >
          <i class="bi bi-map me-2"></i>
          Скрыть карту
        </button>

        <div v-if="showAddMap" class="mt-3">
          <div class="map-box" ref="mapContainer"></div>
          <small class="text-muted d-block mt-2">Кликните по карте, чтобы выбрать точку</small>
        </div>
      </div>
    </div>

    <!-- LIST -->
    <div class="custom-card">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <div class="card-title-custom mb-0">
          <i class="bi bi-list-ul me-2"></i>
          Список мест
        </div>
        <button
          class="btn-filter"
          data-bs-toggle="modal"
          data-bs-target="#locationFilterModal"
        >
          <i class="bi bi-funnel me-2"></i>
          Фильтр по чатам
        </button>
      </div>

      <div v-if="appliedLocationChatFilters.length" class="filter-badge mb-3">
        <i class="bi bi-funnel-fill me-2"></i>
        Выбрано чатов: {{ appliedLocationChatFilters.length }}
      </div>

      <div
        v-if="loading"
        class="loading-box"
      >
        Загрузка...
      </div>

      <div
        v-else-if="visibleLocations.length === 0"
        class="empty-box"
      >
        <i class="bi bi-inbox me-2"></i>
        Список пуст
      </div>

      <div
        v-else
        class="locations-grid"
      >
        <div
          v-for="loc in visibleLocations"
          :key="loc.id"
          class="location-card"
        >
          <div class="location-left">
            <div class="location-icon">
              <i class="bi bi-geo-alt-fill"></i>
            </div>
            <div class="location-info">
              <div class="location-name">
                {{ loc.properties.name }}
              </div>
              <div class="location-chats">
                {{ (loc.properties.chat_titles || []).join(", ") || loc.properties.chat_title || "—" }}
              </div>
              <div class="location-synonyms" v-if="loc.properties.synonyms.length">
                Синонимы: {{ loc.properties.synonyms.join(", ") }}
              </div>
              <div class="location-coords" v-if="hasCoordinates(loc)">
                {{ toFiniteCoord(loc.geometry.coordinates[1]).toFixed(4) }}, {{ toFiniteCoord(loc.geometry.coordinates[0]).toFixed(4) }}
              </div>
            </div>
          </div>

          <div class="item-actions">
            <button
              class="btn-action btn-map"
              data-bs-toggle="modal"
              data-bs-target="#viewLocationMapModal"
              @click="openPreviewModal(loc)"
              :disabled="!hasCoordinates(loc)"
            >
              <i class="bi bi-geo-alt me-1"></i>
              На карте
            </button>

            <button
              class="btn-action btn-edit"
              data-bs-toggle="modal"
              data-bs-target="#editLocationModal"
              @click="openEditModal(loc)"
            >
              <i class="bi bi-pencil-square me-1"></i>
              Ред.
            </button>

            <button
              class="btn-action btn-delete"
              @click="onRemoveLocation(loc)"
            >
              <i class="bi bi-trash3 me-1"></i>
              Удалить
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Filter modal -->
    <div class="modal fade" id="locationFilterModal" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content custom-modal">
          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title fw-bold">Фильтрация словаря мест</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <label class="form-label mb-2">Чаты</label>
            <div class="main-dropdown" ref="filterChatDropdown">
              <button
                class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
                type="button"
                @click="toggleFilterChatDropdown"
              >
                <span v-if="locationChatFilters.length === 0" class="text-muted">Выберите чаты</span>
                <span v-else class="selected-count">Выбрано: {{ locationChatFilters.length }}</span>
                <i class="bi bi-chevron-down ms-2"></i>
              </button>
              <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: showFilterChatDropdown }">
                <div class="dropdown-header-actions">
                  <button
                    type="button"
                    class="dropdown-action-btn"
                    @click="selectAllFilterChats"
                  >
                    <i class="bi bi-check-all me-1"></i>
                    Выбрать все
                  </button>
                  <button
                    type="button"
                    class="dropdown-action-btn danger"
                    @click="resetLocationFilters"
                    v-if="locationChatFilters.length > 0"
                  >
                    <i class="bi bi-x-lg me-1"></i>
                    Сбросить
                  </button>
                </div>
                <div class="dropdown-items-scroll">
                  <label
                    v-for="c in chats"
                    :key="`filter-chat-${c.id}`"
                    class="dropdown-item-custom"
                    :class="{ active: locationChatFilters.includes(c.id) }"
                  >
                    <input
                      type="checkbox"
                      :id="`filter-chat-${c.id}`"
                      :value="c.id"
                      v-model="locationChatFilters"
                      class="form-check-input me-2"
                    />
                    <span>{{ c.title }}</span>
                  </label>
                </div>
              </div>
            </div>
            <small class="text-muted d-block mt-2">Если ничего не выбрано, показываются все места</small>
          </div>
          <div class="modal-footer border-0 pt-0">
            <button type="button" class="btn-cancel" data-bs-dismiss="modal">Закрыть</button>
            <button type="button" class="btn-save" @click="applyLocationFiltersAndClose">
              Применить
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- View map modal -->
    <div class="modal fade" id="viewLocationMapModal" tabindex="-1">
      <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content custom-modal">
          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title fw-bold">{{ locationToView.name || "Место на карте" }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="map-box map-box-preview" ref="previewMapContainer"></div>
            <small class="text-muted d-block mt-2">
              lat: {{ locationToView.lat }}, lon: {{ locationToView.lon }}
            </small>
          </div>
          <div class="modal-footer border-0 pt-0">
            <button class="btn-cancel" data-bs-dismiss="modal">Закрыть</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <div class="modal fade" id="editLocationModal" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content custom-modal">
          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title fw-bold">Редактировать место</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Название</label>
              <input type="text" class="form-control custom-input" v-model="locationToEdit.name" required />
            </div>

            <div class="mb-3">
              <label class="form-label">Чаты</label>
              <div class="main-dropdown" ref="editChatDropdown">
                <button
                  class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
                  type="button"
                  @click="toggleEditChatDropdown"
                >
                  <span v-if="!locationToEdit.chats || locationToEdit.chats.length === 0" class="text-muted">Выберите чаты</span>
                  <span v-else class="selected-count">Выбрано: {{ locationToEdit.chats.length }}</span>
                  <i class="bi bi-chevron-down ms-2"></i>
                </button>
                <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: showEditChatDropdown }">
                  <div class="dropdown-header-actions">
                    <button
                      type="button"
                      class="dropdown-action-btn"
                      @click="selectAllEditChats"
                    >
                      <i class="bi bi-check-all me-1"></i>
                      Выбрать все
                    </button>
                    <button
                      type="button"
                      class="dropdown-action-btn danger"
                      @click="locationToEdit.chats = []"
                      v-if="locationToEdit.chats && locationToEdit.chats.length > 0"
                    >
                      <i class="bi bi-x-lg me-1"></i>
                      Сбросить
                    </button>
                  </div>
                  <div class="dropdown-items-scroll">
                    <label
                      v-for="c in chats"
                      :key="c.id"
                      class="dropdown-item-custom"
                      :class="{ active: locationToEdit.chats && locationToEdit.chats.includes(c.id) }"
                    >
                      <input
                        type="checkbox"
                        :id="`edit-chat-${c.id}`"
                        :value="c.id"
                        v-model="locationToEdit.chats"
                        class="form-check-input me-2"
                      />
                      <span>{{ c.title }}</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <div class="row g-3 mb-3">
              <div class="col-6">
                <label class="form-label">Широта (lat)</label>
                <input type="number" step="0.000001" class="form-control custom-input" v-model="locationToEdit.lat" />
              </div>
              <div class="col-6">
                <label class="form-label">Долгота (lon)</label>
                <input type="number" step="0.000001" class="form-control custom-input" v-model="locationToEdit.lon" />
              </div>
            </div>

            <div class="mb-3">
              <div :key="editMapKey" class="map-box map-box-edit" ref="editMapContainer"></div>
              <small class="text-muted d-block mt-2">Кликните по карте или перетащите маркер</small>
            </div>

            <div class="mb-3">
              <label class="form-label">Синонимы (через запятую)</label>
              <input type="text" class="form-control custom-input" v-model="locationToEdit.synonyms" />
            </div>
          </div>
          <div class="modal-footer border-0 pt-0">
            <button class="btn-cancel" data-bs-dismiss="modal">Отмена</button>
            <button class="btn-save" data-bs-dismiss="modal" @click="onUpdateLocationClick">
              Сохранить
            </button>
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
}

.btn-create:hover {
  background: #0b5ed7;
  transform: translateY(-1px);
}

.btn-map-toggle {
  border: 0;
  background: rgba(13,110,253,0.1);
  color: #0d6efd;
  padding: 10px 16px;
  border-radius: 14px;
  font-weight: 700;
  transition: 0.2s ease;
}

.btn-map-toggle:hover {
  background: rgba(13,110,253,0.2);
}

.btn-filter {
  border: 0;
  background: rgba(13,110,253,0.1);
  color: #0d6efd;
  padding: 10px 16px;
  border-radius: 14px;
  font-weight: 700;
  transition: 0.2s ease;
}

.btn-filter:hover {
  background: rgba(13,110,253,0.2);
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

/* Фильтр */
.filter-badge {
  display: inline-flex;
  align-items: center;
  background: rgba(13,110,253,0.1);
  color: #0d6efd;
  padding: 8px 14px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 14px;
}

/* Карточки локаций */
.locations-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.location-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  padding: 18px;
  border-radius: 20px;
  background: #f8fafc;
  border: 1px solid #eef1f4;
  transition: 0.2s ease;
}

.location-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15,23,42,0.06);
}

.location-left {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  flex: 1;
  min-width: 0;
}

.location-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: rgba(25,135,84,0.1);
  color: #198754;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.location-info {
  min-width: 0;
  flex: 1;
}

.location-name {
  font-size: 16px;
  font-weight: 700;
  color: #111;
  margin-bottom: 4px;
  word-break: break-word;
}

.location-chats {
  font-size: 13px;
  color: #6c757d;
  margin-bottom: 2px;
}

.location-synonyms {
  font-size: 13px;
  color: #6c757d;
  margin-bottom: 2px;
}

.location-coords {
  font-size: 12px;
  color: #adb5bd;
  font-family: 'Courier New', monospace;
}

.item-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

/* Карта */
.map-box {
  width: 100%;
  height: 320px;
  border: 1px solid #eef1f4;
  border-radius: 20px;
  overflow: hidden;
}

.map-box-edit {
  height: 240px;
}

.map-box-preview {
  height: 420px;
}

/* ===== DROPDOWN STYLES (как в навбаре) ===== */
.main-dropdown {
  position: relative;
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

.selected-count {
  font-weight: 600;
  color: #0d6efd;
}

.custom-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  min-width: 100%;
  margin-top: 8px !important;
  padding: 8px;
  border-radius: 18px;
  background: #fff;

  opacity: 0;
  visibility: hidden;
  display: block;
  pointer-events: none;
  transition: opacity 0.18s ease, visibility 0.18s ease;
  z-index: 1050;
}

.main-dropdown .custom-menu.show {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

.dropdown-header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 6px 10px;
  border-bottom: 1px solid #eef1f4;
  margin-bottom: 6px;
}

.dropdown-action-btn {
  border: 0;
  background: transparent;
  color: #0d6efd;
  font-weight: 600;
  font-size: 13px;
  padding: 6px 10px;
  border-radius: 10px;
  transition: 0.2s ease;
  display: flex;
  align-items: center;
}

.dropdown-action-btn:hover {
  background: rgba(13,110,253,0.08);
}

.dropdown-action-btn.danger {
  color: #dc3545;
}

.dropdown-action-btn.danger:hover {
  background: rgba(220,53,69,0.08);
}

.dropdown-items-scroll {
  max-height: 260px;
  overflow-y: auto;
}

.dropdown-item-custom {
  display: flex;
  align-items: center;
  border-radius: 12px;
  padding: 11px 14px;
  font-weight: 600;
  transition: all 0.18s ease;
  cursor: pointer;
  margin-bottom: 2px;
}

.dropdown-item-custom:hover {
  background: #f0f4ff;
  transform: translateX(2px);
}

.dropdown-item-custom.active {
  background: rgba(13,110,253,0.08);
}

.dropdown-item-custom .form-check-input {
  margin-top: 0;
  flex-shrink: 0;
  cursor: pointer;
}

.dropdown-item-custom span {
  font-size: 14px;
  color: #111;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Скроллбар для дропдауна */
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

/* Состояния */
.loading-box,
.empty-box {
  padding: 40px;
  text-align: center;
  color: #6c757d;
  font-weight: 600;
}

/* Модальные окна */
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

  .location-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .item-actions {
    width: 100%;
    flex-direction: column;
  }

  .btn-action,
  .btn-create,
  .btn-map-toggle,
  .btn-filter {
    width: 100%;
  }
}
</style>