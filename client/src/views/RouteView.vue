<script setup>
import axios from "axios";
import { ref, onBeforeMount, computed } from "vue";
import Cookies from "js-cookie";

const routes = ref([]);
const locations = ref([]);
const chats = ref([]);
const loading = ref(false);

const routeToAdd = ref({
    name: "",
    chats: [],
    start_point: null,
    end_point: null,
    enabled: true,
    points: [],
});

const routeToEdit = ref({
    id: null,
    name: "",
    chats: [],
    start_point: null,
    end_point: null,
    enabled: true,
    points: [],
});

function normalizeId(value) {
    const id = Number(value);
    return Number.isFinite(id) && id > 0 ? id : null;
}

function normalizeIdArray(values) {
    const result = [];
    for (const value of values || []) {
        const id = normalizeId(value);
        if (id && !result.includes(id)) result.push(id);
    }
    return result;
}

async function fetchRoutes() {
    loading.value = true;
    const r = await axios.get("/api/routes/");
    routes.value = r.data;
    loading.value = false;
}

async function fetchChats() {
    const r = await axios.get("/api/chats/");
    chats.value = r.data || [];
}

async function fetchLocations() {
    const r = await axios.get("/api/locations/");
    locations.value = (r.data.features || []).map((f) => {
        const props = f.properties || {};
        const m2mChats = Array.isArray(props.chats) ? props.chats : [];
        const fallbackChat = props.chat ? [props.chat] : [];
        const chatIds = normalizeIdArray([...m2mChats, ...fallbackChat]);

        return {
            id: f.id,
            name: props.name,
            synonyms: props.synonyms || [],
            chatIds,
        };
    });
}

function inferRouteChats(route) {
    const chatSet = new Set();
    const locationIds = [
        route.start_point,
        route.end_point,
        ...(route.points || []).map((p) => p.location),
    ];

    for (const rawLocationId of locationIds) {
        const locationId = normalizeId(rawLocationId);
        if (!locationId) continue;
        const loc = locations.value.find((l) => l.id === locationId);
        if (!loc) continue;
        for (const chatId of loc.chatIds) {
            chatSet.add(chatId);
        }
    }

    return Array.from(chatSet);
}

function filteredLocationsByChats(chatIds) {
    const selectedChatIds = normalizeIdArray(chatIds);
    if (!selectedChatIds.length) return [];

    const selectedSet = new Set(selectedChatIds);
    return locations.value.filter((loc) =>
        loc.chatIds.some((chatId) => selectedSet.has(chatId))
    );
}

const addAvailableLocations = computed(() =>
    filteredLocationsByChats(routeToAdd.value.chats)
);

const editAvailableLocations = computed(() =>
    filteredLocationsByChats(routeToEdit.value.chats)
);

const addChatsSelected = computed(() => normalizeIdArray(routeToAdd.value.chats).length > 0);
const editChatsSelected = computed(() => normalizeIdArray(routeToEdit.value.chats).length > 0);

function sanitizeRouteSelections(form, availableLocations) {
    const allowedIds = new Set(availableLocations.map((loc) => loc.id));

    form.chats = normalizeIdArray(form.chats);
    form.start_point = normalizeId(form.start_point);
    form.end_point = normalizeId(form.end_point);

    if (!form.start_point || !allowedIds.has(form.start_point)) {
        form.start_point = null;
    }
    if (!form.end_point || !allowedIds.has(form.end_point)) {
        form.end_point = null;
    }

    form.points = (form.points || [])
        .map((pointId) => normalizeId(pointId))
        .filter((pointId) => pointId && allowedIds.has(pointId));
}

function onAddChatsChange() {
    sanitizeRouteSelections(routeToAdd.value, addAvailableLocations.value);
}

function onEditChatsChange() {
    sanitizeRouteSelections(routeToEdit.value, editAvailableLocations.value);
}

function routePayload(form) {
    return {
        name: form.name,
        chats: normalizeIdArray(form.chats),
        start_point: normalizeId(form.start_point),
        end_point: normalizeId(form.end_point),
        enabled: !!form.enabled,
        points: (form.points || [])
            .map((pointId) => normalizeId(pointId))
            .filter((pointId) => pointId),
    };
}

function extractApiError(error) {
    const data = error?.response?.data;
    if (!data) return "Ошибка запроса";
    if (typeof data === "string") return data;
    if (Array.isArray(data)) return data.join(", ");

    const parts = [];
    for (const [key, value] of Object.entries(data)) {
        if (Array.isArray(value)) {
            parts.push(`${key}: ${value.join(", ")}`);
        } else if (value && typeof value === "object") {
            parts.push(`${key}: ${JSON.stringify(value)}`);
        } else {
            parts.push(`${key}: ${String(value)}`);
        }
    }
    return parts.join(" | ") || "Ошибка запроса";
}

async function addRoute() {
    sanitizeRouteSelections(routeToAdd.value, addAvailableLocations.value);

    if (!routeToAdd.value.chats.length) {
        alert("Выберите хотя бы один чат");
        return;
    }
    if (!routeToAdd.value.start_point || !routeToAdd.value.end_point) {
        alert("Выберите начальную и конечную точки");
        return;
    }

    try {
        await axios.post("/api/routes/", routePayload(routeToAdd.value));
        resetAddForm();
        await fetchRoutes();
    } catch (error) {
        alert(extractApiError(error));
    }
}

function resetAddForm() {
    routeToAdd.value = {
        name: "",
        chats: [],
        start_point: null,
        end_point: null,
        enabled: true,
        points: [],
    };
}

function editRoute(route) {
    const routeChats = normalizeIdArray(route.chats || []);
    const inferredChats = routeChats.length ? routeChats : inferRouteChats(route);

    routeToEdit.value = {
        id: route.id,
        name: route.name,
        chats: inferredChats,
        start_point: normalizeId(route.start_point),
        end_point: normalizeId(route.end_point),
        enabled: route.enabled,
        points: (route.points || []).map((p) => normalizeId(p.location)).filter((x) => x),
    };

    sanitizeRouteSelections(routeToEdit.value, editAvailableLocations.value);
}

async function updateRoute() {
    sanitizeRouteSelections(routeToEdit.value, editAvailableLocations.value);

    if (!routeToEdit.value.chats.length) {
        alert("Выберите хотя бы один чат");
        return;
    }
    if (!routeToEdit.value.start_point || !routeToEdit.value.end_point) {
        alert("Выберите начальную и конечную точки");
        return;
    }

    try {
        await axios.put(`/api/routes/${routeToEdit.value.id}/`, routePayload(routeToEdit.value));
        await fetchRoutes();
    } catch (error) {
        alert(extractApiError(error));
    }
}

async function removeRoute(route) {
    if (!confirm("Удалить маршрут?")) return;
    await axios.delete(`/api/routes/${route.id}/`);
    await fetchRoutes();
}

function addPoint(form) {
    form.points.push(null);
}

function removePoint(form, idx) {
    form.points.splice(idx, 1);
}

function movePointUp(form, idx) {
    if (idx === 0) return;
    [form.points[idx - 1], form.points[idx]] = [form.points[idx], form.points[idx - 1]];
}

function movePointDown(form, idx) {
    if (idx === form.points.length - 1) return;
    [form.points[idx + 1], form.points[idx]] = [form.points[idx], form.points[idx + 1]];
}

onBeforeMount(async () => {
    axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
    await Promise.all([fetchChats(), fetchLocations(), fetchRoutes()]);
});
</script>

<template>
    <div class="container-fluid p-3">
        <h4>Маршруты</h4>

        <form @submit.prevent="addRoute" class="mb-4 border rounded p-3">
            <h6>Новый маршрут</h6>

            <div class="mb-3">
                <label class="form-label mb-1">Чаты</label>
                <div class="chat-checkboxes">
                    <div class="form-check chat-check-item" v-for="c in chats" :key="c.id">
                        <input
                            class="form-check-input"
                            type="checkbox"
                            :id="`add-route-chat-${c.id}`"
                            :value="c.id"
                            v-model="routeToAdd.chats"
                            @change="onAddChatsChange"
                        />
                        <label class="form-check-label" :for="`add-route-chat-${c.id}`">{{ c.title }}</label>
                    </div>
                </div>
            </div>

            <div class="row g-2 mb-2">
                <div class="col-12 col-lg-4">
                    <input class="form-control" v-model="routeToAdd.name" placeholder="Название маршрута" required />
                </div>
                <div class="col-12 col-md-6 col-lg-3">
                    <select class="form-select" v-model="routeToAdd.start_point" :disabled="!addChatsSelected" required>
                        <option :value="null" disabled>Начальная точка</option>
                        <option v-for="l in addAvailableLocations" :key="l.id" :value="l.id">
                            {{ l.name }}
                        </option>
                    </select>
                </div>
                <div class="col-12 col-md-6 col-lg-3">
                    <select class="form-select" v-model="routeToAdd.end_point" :disabled="!addChatsSelected" required>
                        <option :value="null" disabled>Конечная точка</option>
                        <option v-for="l in addAvailableLocations" :key="l.id" :value="l.id">
                            {{ l.name }}
                        </option>
                    </select>
                </div>
                <div class="col-12 col-lg-2 d-flex align-items-center">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="routeEnabledAdd" v-model="routeToAdd.enabled" />
                        <label class="form-check-label" for="routeEnabledAdd">Включён</label>
                    </div>
                </div>
            </div>

            <div class="mb-2">
                <strong>Точки маршрута</strong>
                <div v-for="(pid, idx) in routeToAdd.points" :key="idx" class="d-flex gap-2 align-items-center mb-1">
                    <select class="form-select" v-model="routeToAdd.points[idx]" :disabled="!addChatsSelected" required>
                        <option :value="null" disabled>Выбрать точку</option>
                        <option v-for="l in addAvailableLocations" :key="l.id" :value="l.id">
                            {{ l.name }}
                        </option>
                    </select>

                    <button type="button" class="btn btn-sm btn-outline-secondary" @click="movePointUp(routeToAdd, idx)">▲</button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" @click="movePointDown(routeToAdd, idx)">▼</button>
                    <button type="button" class="btn btn-sm btn-outline-danger" @click="removePoint(routeToAdd, idx)">✕</button>
                </div>

                <button type="button" class="btn btn-sm btn-outline-primary mt-1" :disabled="!addChatsSelected" @click="addPoint(routeToAdd)">
                    + добавить точку
                </button>
            </div>

            <button class="btn btn-primary">Создать маршрут</button>
        </form>

        <div v-if="loading">Загрузка...</div>

        <div v-else>
            <div v-for="r in routes" :key="r.id" class="route-item">
                <div>
                    <div class="fw-bold">{{ r.name }}</div>
                    <div class="text-muted">{{ r.start_point_name }} → {{ r.end_point_name }}</div>
                    <div class="small" v-if="(r.chat_titles || []).length">
                        Чаты: {{ r.chat_titles.join(", ") }}
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
                    <button class="btn btn-warning" data-bs-toggle="modal" data-bs-target="#editRouteModal" @click="editRoute(r)">
                        <i class="bi bi-pen-fill"></i>
                    </button>
                    <button class="btn btn-danger" @click="removeRoute(r)">
                        <i class="bi bi-trash3-fill"></i>
                    </button>
                </div>
            </div>
        </div>

        <div class="modal fade" id="editRouteModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5>Редактировать маршрут</h5>
                        <button class="btn-close" data-bs-dismiss="modal"></button>
                    </div>

                    <div class="modal-body">
                        <input class="form-control mb-2" v-model="routeToEdit.name" />

                        <div class="mb-2">
                            <label class="form-label mb-1">Чаты</label>
                            <div class="chat-checkboxes">
                                <div class="form-check chat-check-item" v-for="c in chats" :key="c.id">
                                    <input
                                        class="form-check-input"
                                        type="checkbox"
                                        :id="`edit-route-chat-${c.id}`"
                                        :value="c.id"
                                        v-model="routeToEdit.chats"
                                        @change="onEditChatsChange"
                                    />
                                    <label class="form-check-label" :for="`edit-route-chat-${c.id}`">{{ c.title }}</label>
                                </div>
                            </div>
                        </div>

                        <div class="row g-2 mb-2">
                            <div class="col">
                                <select class="form-select" v-model="routeToEdit.start_point" :disabled="!editChatsSelected">
                                    <option v-for="l in editAvailableLocations" :key="l.id" :value="l.id">
                                        {{ l.name }}
                                    </option>
                                </select>
                            </div>
                            <div class="col">
                                <select class="form-select" v-model="routeToEdit.end_point" :disabled="!editChatsSelected">
                                    <option v-for="l in editAvailableLocations" :key="l.id" :value="l.id">
                                        {{ l.name }}
                                    </option>
                                </select>
                            </div>
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="checkbox" v-model="routeToEdit.enabled" id="enabledEditRoute" />
                                <label class="form-check-label" for="enabledEditRoute">Включён</label>
                            </div>
                        </div>

                        <div v-for="(pid, idx) in routeToEdit.points" :key="idx" class="d-flex gap-2 mb-1">
                            <select class="form-select" v-model="routeToEdit.points[idx]" :disabled="!editChatsSelected">
                                <option v-for="l in editAvailableLocations" :key="l.id" :value="l.id">
                                    {{ l.name }}
                                </option>
                            </select>
                            <button class="btn btn-sm btn-outline-danger" @click="removePoint(routeToEdit, idx)">✕</button>
                        </div>

                        <button class="btn btn-sm btn-outline-primary" :disabled="!editChatsSelected" @click="addPoint(routeToEdit)">
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
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 8px;
    margin-bottom: 0.5rem;
}

.route-actions {
    display: flex;
    gap: 0.5rem;
}

.route-status {
    font-size: 0.85rem;
    color: green;
}

.route-status.off {
    color: red;
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
