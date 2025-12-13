<script setup>
import axios from "axios"
import { ref, onBeforeMount, computed } from "vue"
import Cookies from "js-cookie"

const routes = ref([])
const locations = ref([])
const loading = ref(false)

const routeToAdd = ref({
    name: "",
    start_point: null,
    end_point: null,
    enabled: true,
    points: []
})

const routeToEdit = ref({})

/* ---------- API ---------- */

async function fetchRoutes() {
    loading.value = true
    const r = await axios.get("/api/routes/")
    routes.value = r.data
    loading.value = false
}

async function fetchLocations() {
    const r = await axios.get("/api/locations/")
    locations.value = r.data.features.map(f => ({
        id: f.id,
        name: f.properties.name,
        synonyms: f.properties.synonyms
    }))
}

/* ---------- helpers ---------- */

function locationName(id) {
    const l = locations.value.find(x => x.id === id)
    return l ? l.name : "—"
}

/* ---------- CRUD ---------- */

async function addRoute() {
    await axios.post("/api/routes/", routeToAdd.value)
    resetAddForm()
    await fetchRoutes()
}

function resetAddForm() {
    routeToAdd.value = {
        name: "",
        start_point: null,
        end_point: null,
        enabled: true,
        points: []
    }
}

function editRoute(route) {
    routeToEdit.value = {
        id: route.id,
        name: route.name,
        start_point: route.start_point,
        end_point: route.end_point,
        enabled: route.enabled,
        points: route.points.map(p => p.location)
    }
}

async function updateRoute() {
    await axios.put(`/api/routes/${routeToEdit.value.id}/`, routeToEdit.value)
    await fetchRoutes()
}

async function removeRoute(route) {
    if (!confirm("Удалить маршрут?")) return
    await axios.delete(`/api/routes/${route.id}/`)
    await fetchRoutes()
}

/* ---------- points order ---------- */

function addPoint(form) {
    form.points.push(null)
}

function removePoint(form, idx) {
    form.points.splice(idx, 1)
}

function movePointUp(form, idx) {
    if (idx === 0) return
        ;[form.points[idx - 1], form.points[idx]] =
            [form.points[idx], form.points[idx - 1]]
}

function movePointDown(form, idx) {
    if (idx === form.points.length - 1) return
        ;[form.points[idx + 1], form.points[idx]] =
            [form.points[idx], form.points[idx + 1]]
}

/* ---------- init ---------- */

onBeforeMount(() => {
    axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken")
    fetchLocations()
    fetchRoutes()
})
</script>

<template>
    <div class="container-fluid p-3">
        <h4>Маршруты</h4>

        <!-- Добавление маршрута -->
        <form @submit.prevent="addRoute" class="mb-4 border rounded p-3">
            <h6>Новый маршрут</h6>

            <div class="row g-2 mb-2">
                <div class="col">
                    <input class="form-control" v-model="routeToAdd.name" placeholder="Название маршрута" required />
                </div>
                <div class="col">
                    <select class="form-select" v-model="routeToAdd.start_point" required>
                        <option :value="null" disabled>Начальная точка</option>
                        <option v-for="l in locations" :key="l.id" :value="l.id">
                            {{ l.name }}
                        </option>
                    </select>
                </div>
                <div class="col">
                    <select class="form-select" v-model="routeToAdd.end_point" required>
                        <option :value="null" disabled>Конечная точка</option>
                        <option v-for="l in locations" :key="l.id" :value="l.id">
                            {{ l.name }}
                        </option>
                    </select>
                </div>
                <div class="col-auto">
                    <input type="checkbox" v-model="routeToAdd.enabled" /> Включён
                </div>

            </div>

            <!-- Точки -->
            <div class="mb-2">
                <strong>Точки маршрута</strong>
                <div v-for="(pid, idx) in routeToAdd.points" :key="idx" class="d-flex gap-2 align-items-center mb-1">
                    <select class="form-select" v-model="routeToAdd.points[idx]" required>
                        <option :value="null" disabled>Выбрать точку</option>
                        <option v-for="l in locations" :key="l.id" :value="l.id">
                            {{ l.name }}
                        </option>
                    </select>

                    <button type="button" class="btn btn-sm btn-outline-secondary"
                        @click="movePointUp(routeToAdd, idx)">▲</button>
                    <button type="button" class="btn btn-sm btn-outline-secondary"
                        @click="movePointDown(routeToAdd, idx)">▼</button>
                    <button type="button" class="btn btn-sm btn-outline-danger"
                        @click="removePoint(routeToAdd, idx)">✕</button>
                </div>

                <button type="button" class="btn btn-sm btn-outline-primary mt-1" @click="addPoint(routeToAdd)">
                    + добавить точку
                </button>
            </div>

            <button class="btn btn-primary">Создать маршрут</button>
        </form>

        <!-- Список маршрутов -->
        <div v-if="loading">Загрузка...</div>

        <div v-else>
            <div v-for="r in routes" :key="r.id" class="route-item">
                <div>
                    <div class="fw-bold">{{ r.name }}</div>
                    <div class="text-muted">
                        {{ r.start_point_name }} → {{ r.end_point_name }}
                    </div>
                    <div class="small">
                        <span v-for="(p, i) in r.points" :key="p.id">
                            {{ p.location_name }}<span v-if="i < r.points.length - 1"> → </span>
                        </span>
                    </div>
                    <div class="route-status" :class="{ off: !r.enabled }">
                        {{ r.enabled ? "Включён" : "Выключен" }}
                    </div>
                </div>

                <div class="route-actions">
                    <button class="btn btn-warning" data-bs-toggle="modal" data-bs-target="#editRouteModal"
                        @click="editRoute(r)">
                        <i class="bi bi-pen-fill"></i>
                    </button>
                    <button class="btn btn-danger" @click="removeRoute(r)">
                        <i class="bi bi-trash3-fill"></i>
                    </button>
                </div>
            </div>
        </div>

        <!-- Модалка редактирования -->
        <div class="modal fade" id="editRouteModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5>Редактировать маршрут</h5>
                        <button class="btn-close" data-bs-dismiss="modal"></button>
                    </div>

                    <div class="modal-body">
                        <input class="form-control mb-2" v-model="routeToEdit.name" />

                        <div class="row g-2 mb-2">
                            <div class="col">
                                <select class="form-select" v-model="routeToEdit.start_point">
                                    <option v-for="l in locations" :key="l.id" :value="l.id">
                                        {{ l.name }}
                                    </option>
                                </select>
                            </div>
                            <div class="col">
                                <select class="form-select" v-model="routeToEdit.end_point">
                                    <option v-for="l in locations" :key="l.id" :value="l.id">
                                        {{ l.name }}
                                    </option>
                                </select>
                            </div>
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="checkbox" v-model="routeToEdit.enabled"
                                    id="enabledEditRoute" />
                                <label class="form-check-label" for="enabledEditRoute">
                                    Включён
                                </label>
                            </div>
                        </div>

                        <div v-for="(pid, idx) in routeToEdit.points" :key="idx" class="d-flex gap-2 mb-1">
                            <select class="form-select" v-model="routeToEdit.points[idx]">
                                <option v-for="l in locations" :key="l.id" :value="l.id">
                                    {{ l.name }}
                                </option>
                            </select>
                            <button class="btn btn-sm btn-outline-danger"
                                @click="removePoint(routeToEdit, idx)">✕</button>
                        </div>

                        <button class="btn btn-sm btn-outline-primary" @click="addPoint(routeToEdit)">
                            + добавить точку
                        </button>
                    </div>

                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button class="btn btn-primary" data-bs-dismiss="modal" @click="updateRoute">
                            Сохранить
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.route-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: .5rem;
    border: 1px solid #ddd;
    border-radius: 8px;
    margin-bottom: .5rem;
}

.route-actions {
    display: flex;
    gap: .5rem;
}

.route-status {
    font-size: .85rem;
    color: green;
}

.route-status.off {
    color: red;
}
</style>