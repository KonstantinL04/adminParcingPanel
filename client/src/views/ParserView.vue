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
const messageFilterCategory = ref("");
const messageFilterChat = ref("");
const messageFilterAuthor = ref("");
const messageFilterDateFrom = ref("");
const messageFilterDateTo = ref("");
const messageFilterTimeFrom = ref("");
const messageFilterTimeTo = ref("");

function toTimestamp(dateValue) {
    const ts = new Date(dateValue || "").getTime();
    return Number.isFinite(ts) ? ts : 0;
}

const messageCategories = computed(() => {
    return [...new Set(messages.value.map((m) => m.category_name).filter(Boolean))];
});

const messageChats = computed(() => {
    return [...new Set(messages.value.map((m) => m.chat_title).filter(Boolean))];
});

const sortedMessages = computed(() => {
    return [...messages.value]
        .filter((msg) => {
            if (messageFilterCategory.value && msg.category_name !== messageFilterCategory.value) return false;
            if (messageFilterChat.value && msg.chat_title !== messageFilterChat.value) return false;
            if (
                messageFilterAuthor.value &&
                !(msg.author_name || "").toLowerCase().includes(messageFilterAuthor.value.toLowerCase())
            ) return false;

            const created = msg.created_at ? new Date(msg.created_at) : null;
            const createdTs = created ? created.getTime() : NaN;

            if (messageFilterDateFrom.value && Number.isFinite(createdTs)) {
                const from = new Date(`${messageFilterDateFrom.value}T00:00:00`).getTime();
                if (createdTs < from) return false;
            }
            if (messageFilterDateTo.value && Number.isFinite(createdTs)) {
                const to = new Date(`${messageFilterDateTo.value}T23:59:59`).getTime();
                if (createdTs > to) return false;
            }

            if ((messageFilterTimeFrom.value || messageFilterTimeTo.value) && Number.isFinite(createdTs)) {
                const h = created.getHours().toString().padStart(2, "0");
                const m = created.getMinutes().toString().padStart(2, "0");
                const msgTime = `${h}:${m}`;
                if (messageFilterTimeFrom.value && msgTime < messageFilterTimeFrom.value) return false;
                if (messageFilterTimeTo.value && msgTime > messageFilterTimeTo.value) return false;
            }
            return true;
        })
        .sort((a, b) => toTimestamp(b.created_at) - toTimestamp(a.created_at));
});

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

function resetMessageFilters() {
    messageFilterCategory.value = "";
    messageFilterChat.value = "";
    messageFilterAuthor.value = "";
    messageFilterDateFrom.value = "";
    messageFilterDateTo.value = "";
    messageFilterTimeFrom.value = "";
    messageFilterTimeTo.value = "";
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
            <div class="d-flex align-items-center justify-content-between gap-2">
                <h5 class="mb-0">Спаршенные сообщения</h5>
                <button
                    class="btn btn-outline-secondary btn-sm"
                    data-bs-toggle="modal"
                    data-bs-target="#messageFilterModal"
                >
                    Фильтр
                </button>
            </div>
            <div v-if="!sortedMessages.length" class="text-muted">Сообщений пока нет</div>

            <div v-else class="mt-3">
                <div v-for="msg in sortedMessages" :key="msg.telegram_message_id" class="message-item">
                    <div class="message-head">
                        <div class="message-chat">{{ msg.chat_title || "Без чата" }}</div>
                        <div class="message-date">{{ formatDate(msg.created_at) }}</div>
                    </div>

                    <div class="message-body">{{ msg.text || "-" }}</div>

                    <div class="message-meta">
                        <span><b>ID:</b> {{ msg.telegram_message_id }}</span>
                        <span><b>Автор:</b> {{ msg.author_name || "-" }}</span>
                        <span><b>Категория:</b> {{ msg.category_name || "-" }}</span>
                    </div>
                </div>
            </div>
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

        <!-- Message filter modal -->
        <div class="modal fade" id="messageFilterModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Фильтрация сообщений</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-2">
                            <label class="form-label">Категория</label>
                            <select class="form-select" v-model="messageFilterCategory">
                                <option value="">Все категории</option>
                                <option v-for="cat in messageCategories" :key="cat" :value="cat">{{ cat }}</option>
                            </select>
                        </div>
                        <div class="mb-2">
                            <label class="form-label">Чат</label>
                            <select class="form-select" v-model="messageFilterChat">
                                <option value="">Все чаты</option>
                                <option v-for="chat in messageChats" :key="chat" :value="chat">{{ chat }}</option>
                            </select>
                        </div>
                        <div>
                            <label class="form-label">Автор</label>
                            <input
                                v-model="messageFilterAuthor"
                                type="text"
                                class="form-control"
                                placeholder="Введите имя автора"
                            />
                        </div>
                        <div class="row g-2 mt-1">
                            <div class="col-6">
                                <label class="form-label">Дата с</label>
                                <input v-model="messageFilterDateFrom" type="date" class="form-control" />
                            </div>
                            <div class="col-6">
                                <label class="form-label">Дата по</label>
                                <input v-model="messageFilterDateTo" type="date" class="form-control" />
                            </div>
                        </div>
                        <div class="row g-2 mt-1">
                            <div class="col-6">
                                <label class="form-label">Время с</label>
                                <input v-model="messageFilterTimeFrom" type="time" class="form-control" />
                            </div>
                            <div class="col-6">
                                <label class="form-label">Время по</label>
                                <input v-model="messageFilterTimeTo" type="time" class="form-control" />
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-outline-secondary" @click="resetMessageFilters">
                            Сбросить
                        </button>
                        <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                            Применить
                        </button>
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

.message-item {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    padding: 0.7rem 0.85rem;
    margin: 0.55rem 0;
    border: 1px solid #ddd;
    border-radius: 8px;
    background: #fff;
}

.message-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
}

.message-chat {
    font-weight: 600;
    font-size: 1rem;
}

.message-date {
    font-size: 0.85rem;
    color: #6c757d;
    white-space: nowrap;
}

.message-body {
    font-size: 0.95rem;
    line-height: 1.3;
    white-space: pre-wrap;
    word-break: break-word;
}

.message-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.9rem;
    color: #495057;
    font-size: 0.85rem;
}
</style>
