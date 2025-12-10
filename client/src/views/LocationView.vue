<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";

const locations = ref([]);
const loading = ref(false);

const locationToAdd = ref({
  name: "",
  lat: "",
  lon: "",
  synonyms: "",
});

const locationToEdit = ref({});

async function fetchLocations() {
  loading.value = true;
  const r = await axios.get("/api/locations/");
  locations.value = r.data.features || []; // ожидаем GeoJSON
  loading.value = false;
}

async function onAddLocation() {
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
    }
  });

  locationToAdd.value = { name: "", lat: "", lon: "", synonyms: "" };
  await fetchLocations();
}

function onEditLocationClick(loc) {
  locationToEdit.value = {
    id: loc.id,
    name: loc.properties.name,
    lat: loc.geometry.coordinates[1],
    lon: loc.geometry.coordinates[0],
    synonyms: loc.properties.synonyms.join(", "),
  };
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
  await fetchLocations();
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
            <input type="number" step="0.000001" class="form-control" v-model="locationToAdd.lat" required />
            <label>Широта (lat)</label>
          </div>
        </div>

        <div class="col-2">
          <div class="form-floating">
            <input type="number" step="0.000001" class="form-control" v-model="locationToAdd.lon" required />
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

    <div v-if="loading" class="mt-3">Загрузка...</div>

    <!-- List -->
    <div v-else class="mt-3">
      <div v-for="loc in locations" :key="loc.id" class="item-box">

        <div>
          <strong>{{ loc.properties.name }}</strong>
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
</style>