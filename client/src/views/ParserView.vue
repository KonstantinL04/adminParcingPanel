<script setup>
import axios from "axios";
import { ref, onMounted, onUnmounted, computed } from "vue";
import Cookies from "js-cookie";

// --- Парсер ---
const parserRunning = ref(false);
let intervalId = null;
const parserBusy = ref(false);
const parserError = ref("");

axios.defaults.withCredentials = true;
axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");

async function fetchParserStatus() {
    try {
        const r = await axios.get("/api/parser/status/");
        parserRunning.value = !!r.data.running;
        parserError.value = "";
    } catch (e) {
        console.error("Ошибка получения статуса парсера:", e);
        parserError.value = "Не удалось получить статус парсера (возможно, нет доступа).";
    }
}

async function startParser() {
    if (parserBusy.value) return;
    parserBusy.value = true;
    try {
        await axios.post("/api/parser/start/");
        parserError.value = "";
    } catch (e) {
        console.error("Ошибка запуска парсера:", e);
        parserError.value = "Не удалось запустить парсер (возможно, нет доступа).";
    } finally {
        parserBusy.value = false;
        await fetchParserStatus();
    }
}

async function stopParser() {
    if (parserBusy.value) return;
    parserBusy.value = true;
    try {
        await axios.post("/api/parser/stop/");
        parserError.value = "";
    } catch (e) {
        console.error("Ошибка остановки парсера:", e);
        parserError.value = "Не удалось остановить парсер (возможно, нет доступа).";
    } finally {
        parserBusy.value = false;
        await fetchParserStatus();
    }
}

// --- Вкладки ---
const activeTab = ref("messages");

// --- Данные ---
const messages = ref([]);
const roadEvents = ref([]);
const selectedEvent = ref(null);
async function fetchMessages() {
    const r = await axios.get("/api/events/messages/");
    messages.value = r.data?.results || r.data;
}

async function fetchRoadEvents() {
    const r = await axios.get("/api/events/road-events/");
    roadEvents.value = r.data?.results || r.data;
}

function fetchAll() {
    fetchMessages();
    fetchRoadEvents();
}

const eventMapUrl = computed(() => {
    if (!selectedEvent.value) return "";
    const coords = selectedEvent.value.location?.coordinates;
    if (!coords || coords.length < 2) return "";
    const lon = coords[0];
    const lat = coords[1];
    const delta = 0.01;
    const bbox = [lon - delta, lat - delta, lon + delta, lat + delta].join("%2C");
    return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat}%2C${lon}`;
});

function openEventMap(ev) {
    selectedEvent.value = ev;
}

function formatDate(value) {
    if (!value) return "";
    try {
        return new Date(value).toLocaleString();
    } catch {
        return value;
    }
}

function timeLeft(validUntil) {
    if (!validUntil) return "";
    const diff = new Date(validUntil).getTime() - Date.now();
    if (isNaN(diff)) return "";
    if (diff <= 0) return "истекло";
    const mins = Math.ceil(diff / 60000);
    return `${mins} мин`;
}

// --- Интервалы для обновления ---
onMounted(() => {
    fetchParserStatus();
    fetchAll();
    intervalId = setInterval(fetchParserStatus, 5000);
});

onUnmounted(() => {
    if (intervalId) clearInterval(intervalId);
});
</script>

<template>
    <div class="container-fluid p-3">

        <!-- Управление парсером -->
        <div class="mb-4">
            <h4>Управление Telethon-парсером</h4>
            <button class="btn btn-success me-2" :disabled="parserRunning || parserBusy" @click="startParser">▶ Запустить
                парсер</button>
            <button class="btn btn-danger" :disabled="!parserRunning || parserBusy" @click="stopParser">⏹ Остановить парсер</button>
            <p class="mt-2">
                <strong>Статус:</strong>
                <span :class="parserRunning ? 'text-success' : 'text-danger'">
                    {{ parserRunning ? "Запущен" : "Остановлен" }}
                </span>
            </p>
            <p v-if="parserError" class="text-danger mb-0">{{ parserError }}</p>
        </div>

        <!-- Вкладки -->
        <ul class="nav nav-tabs mb-3">
            <li class="nav-item">
                <button class="nav-link" :class="{ active: activeTab === 'messages' }"
                    @click="activeTab = 'messages'">Сообщения</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" :class="{ active: activeTab === 'road-events' }"
                    @click="activeTab = 'road-events'">Дорожные события</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" :class="{ active: activeTab === 'relevance' }"
                    @click="activeTab = 'relevance'">Актуальность</button>
            </li>
        </ul>

        <!-- Контент вкладок -->
        <div v-if="activeTab === 'messages'">
            <h5>Спаршенные сообщения</h5>
            <table class="table table-striped table-bordered">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Чат</th>
                        <th>Автор</th>
                        <th>Категория</th>
                        <th>Текст</th>
                        <th>Дата</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="msg in messages" :key="msg.telegram_message_id">
                        <td>{{ msg.telegram_message_id }}</td>
                        <td>{{ msg.chat_title }}</td>
                        <td>{{ msg.author_name }}</td>
                        <td>{{ msg.category_name }}</td>
                        <td>{{ msg.text }}</td>
                        <td>{{ msg.created_at }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div v-if="activeTab === 'road-events'">
            <h5>Дорожные события</h5>
            <table class="table table-striped table-bordered">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Категория</th>
                        <th>Координаты</th>
                        <th>Статус</th>
                        <th>Подтв.</th>
                        <th>Источник</th>
                        <th>Создано</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="ev in roadEvents" :key="ev.id">
                        <td>{{ ev.id }}</td>
                        <td>{{ ev.category_label || ev.category_code }}</td>
                        <td>
                            <a href="#" data-bs-toggle="modal" data-bs-target="#eventMapModal" @click.prevent="openEventMap(ev)">
                                {{ ev.location?.coordinates?.[1] }}, {{ ev.location?.coordinates?.[0] }}
                            </a>
                        </td>
                        <td>{{ ev.status }}</td>
                        <td>{{ ev.confirmations }}</td>
                        <td>{{ ev.source }}</td>
                        <td>{{ formatDate(ev.created_at) }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div v-if="activeTab === 'relevance'">
            <h5>Актуальность событий</h5>
            <table class="table table-striped table-bordered">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Категория</th>
                        <th>Статус</th>
                        <th>Подтв.</th>
                        <th>Valid until</th>
                        <th>Осталось</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="ev in roadEvents" :key="ev.id">
                        <td>{{ ev.id }}</td>
                        <td>{{ ev.category_label || ev.category_code }}</td>
                        <td>{{ ev.status }}</td>
                        <td>{{ ev.confirmations }}</td>
                        <td>{{ formatDate(ev.valid_until) }}</td>
                        <td>{{ timeLeft(ev.valid_until) }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Map modal -->
        <div class="modal fade" id="eventMapModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Место события</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div v-if="eventMapUrl">
                            <iframe :src="eventMapUrl" width="100%" height="400" style="border:0;"></iframe>
                        </div>
                        <div v-else class="text-muted">Нет координат</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.table {
    font-size: 0.9rem;
}
</style>
