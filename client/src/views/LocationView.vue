<script setup>
import axios from "axios";
import { ref, onBeforeMount, onMounted } from "vue";
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
  chat: "",
  region: "",
  city: "",
});

const locationToEdit = ref({});
const mapContainer = ref(null);
const mapState = ref({ map: null, marker: null });
const DEFAULT_CENTER = [52.2896, 104.2806]; // Иркутск по умолчанию

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
      chat: locationToAdd.value.chat ? parseInt(locationToAdd.value.chat) : null,
      city: locationToAdd.value.city ? parseInt(locationToAdd.value.city) : null,
    }
  });

  locationToAdd.value = { name: "", lat: "", lon: "", synonyms: "", chat: "", region: "", city: "" };
  await fetchLocations();
}

function onEditLocationClick(loc) {
  const regionId = loc.properties.region_id || "";
  locationToEdit.value = {
    id: loc.id,
    name: loc.properties.name,
    lat: loc.geometry.coordinates[1],
    lon: loc.geometry.coordinates[0],
    synonyms: loc.properties.synonyms.join(", "),
    chat: loc.properties.chat || "",
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
      chat: locationToEdit.value.chat ? parseInt(locationToEdit.value.chat) : null,
      city: locationToEdit.value.city ? parseInt(locationToEdit.value.city) : null,
    }
  });

  await fetchLocations();
}

async function onRemoveLocation(loc) {
  await axios.delete(`/api/locations/${loc.id}/`);
  await fetchLocations();
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await fetchGeoRefs();
  await fetchLocations();
});

onMounted(() => {
  initMap();
});
</script>

<template>
  <div class="p-3">
    <h4>Словарь мест</h4>

    <!-- Добавление -->
    <form @submit.prevent="onAddLocation" class="mt-3">
      <div class="row g-2">

        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="locationToAdd.name" required />
            <label>Название</label>
          </div>
        </div>

        <div class="col-2">
          <div class="form-floating">
            <select class="form-select" v-model="locationToAdd.chat" required>
              <option value="">—</option>
              <option v-for="c in chats" :key="c.id" :value="c.id">{{ c.title }}</option>
            </select>
            <label>Чат</label>
          </div>
        </div>

        <div class="col-2">
          <div class="form-floating">
            <select class="form-select" v-model="locationToAdd.region" @change="onAddRegionChange" required>
              <option value="">—</option>
              <option v-for="r in filteredRegions" :key="r.id" :value="r.id">{{ r.name }}</option>
            </select>
            <label>Область</label>
          </div>
        </div>

        <div class="col-2">
          <div class="form-floating">
            <select class="form-select" v-model="locationToAdd.city" required>
              <option value="">—</option>
              <option v-for="c in filteredCities" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
            <label>Город</label>
          </div>
        </div>

        <div class="col-2">
          <div class="form-floating">
            <input type="number" step="0.000001" class="form-control" v-model="locationToAdd.lat" readonly required />
            <label>Широта (lat)</label>
          </div>
        </div>

        <div class="col-2">
          <div class="form-floating">
            <input type="number" step="0.000001" class="form-control" v-model="locationToAdd.lon" readonly required />
            <label>Долгота (lon)</label>
          </div>
        </div>

        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="locationToAdd.synonyms" />
            <label>Синонимы (через запятую)</label>
          </div>
        </div>

        <div class="col-auto">
          <button class="btn btn-primary">Добавить</button>
        </div>

      </div>
    </form>

    <div class="mt-3">
      <div class="map-box" ref="mapContainer"></div>
      <small class="text-muted">Кликните по карте, чтобы выбрать точку.</small>
    </div>

    <div v-if="loading" class="mt-3">Загрузка...</div>

    <!-- List -->
    <div v-else class="mt-3">
      <div v-for="loc in locations" :key="loc.id" class="item-box">

        <div>
          <strong>{{ loc.properties.name }}</strong>
          <br>
          <small class="text-muted">
            {{ loc.properties.chat_title || "-" }} /
            {{ loc.properties.region_name || "-" }} /
            {{ loc.properties.city_name || "-" }}
          </small>
          <br>
          <small>
            📍 lat: {{ loc.geometry.coordinates[1] }},
            lon: {{ loc.geometry.coordinates[0] }}
          </small>
          <br>
          <small class="text-muted">
            Синонимы: 
            <span v-if="loc.properties.synonyms.length">{{ loc.properties.synonyms.join(", ") }}</span>
            <span v-else>-</span>
          </small>
        </div>

        <div class="item-actions">
          <button class="btn btn-warning" data-bs-toggle="modal" data-bs-target="#editLocationModal"
            @click="onEditLocationClick(loc)">
            <i class="bi bi-pen-fill"></i>
          </button>

          <button class="btn btn-danger" @click="onRemoveLocation(loc)">
            <i class="bi bi-trash3-fill"></i>
          </button>
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

            <div class="form-floating mb-2">
              <select class="form-select" v-model="locationToEdit.chat" disabled>
                <option value="">—</option>
                <option v-for="c in chats" :key="c.id" :value="c.id">{{ c.title }}</option>
              </select>
              <label>Чат</label>
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
  gap: .5rem;
}
.map-box {
  width: 100%;
  height: 320px;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
}
</style>
