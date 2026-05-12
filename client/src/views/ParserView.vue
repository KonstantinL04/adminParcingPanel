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
    <div class="page-wrap">

        <!-- HEADER -->

        <div class="page-header mb-4">

            <div>
                <h2 class="page-title">
                    <i class="bi bi-cpu-fill me-2"></i>
                    Управление парсером
                </h2>

                <div class="page-subtitle">
                    Мониторинг сообщений Telethon-парсера
                </div>
            </div>

        </div>

        <!-- PARSER -->

        <div class="custom-card mb-4">

            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3">

                <div>

                    <div class="card-title-custom mb-2">
                        Telethon Parser
                    </div>

                    <div
                        class="parser-status"
                        :class="parserRunning ? 'running' : 'stopped'"
                    >
                        <i
                            class="bi"
                            :class="parserRunning ? 'bi-play-circle-fill' : 'bi-stop-circle-fill'"
                        ></i>

                        {{ parserRunning ? "Парсер запущен" : "Парсер остановлен" }}
                    </div>

                    <div
                        v-if="parserError"
                        class="custom-alert mt-3"
                    >
                        {{ parserError }}
                    </div>

                </div>

                <div class="d-flex gap-2">

                    <button
                        class="btn-parser btn-start"
                        :disabled="parserRunning || parserBusy"
                        @click="startParser"
                    >
                        <i class="bi bi-play-fill me-2"></i>
                        Запустить
                    </button>

                    <button
                        class="btn-parser btn-stop"
                        :disabled="!parserRunning || parserBusy"
                        @click="stopParser"
                    >
                        <i class="bi bi-stop-fill me-2"></i>
                        Остановить
                    </button>

                </div>

            </div>

        </div>

        <!-- MESSAGES -->

        <div class="custom-card">

            <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-4">

                <div>

                    <div class="card-title-custom mb-1">
                        Спаршенные сообщения
                    </div>

                    <div class="page-subtitle">
                        Всего сообщений: {{ sortedMessages.length }}
                    </div>

                </div>

                <button
                    class="btn-filter"
                    data-bs-toggle="modal"
                    data-bs-target="#messageFilterModal"
                >
                    <i class="bi bi-funnel-fill me-2"></i>
                    Фильтр
                </button>

            </div>

            <div
                v-if="!sortedMessages.length"
                class="empty-box"
            >
                <i class="bi bi-chat-left-text"></i>

                <div class="mt-2">
                    Сообщений пока нет
                </div>
            </div>

            <div v-else>

                <div
                    v-for="msg in sortedMessages"
                    :key="msg.telegram_message_id"
                    class="message-item"
                >

                    <div class="message-head">

                        <div>

                            <div class="message-chat">
                                {{ msg.chat_title || "Без чата" }}
                            </div>

                            <div class="message-author">
                                <i class="bi bi-person-circle me-1"></i>
                                {{ msg.author_name || "Неизвестный автор" }}
                            </div>

                        </div>

                        <div class="message-date">
                            {{ formatDate(msg.created_at) }}
                        </div>

                    </div>

                    <div class="message-body">
                        {{ msg.text || "-" }}
                    </div>

                    <div class="message-meta">

                        <span class="message-badge">
                            <b>ID:</b>&nbsp;{{ msg.telegram_message_id }}
                        </span>

                        <span class="message-badge">
                            <b>Категория:</b>&nbsp;{{ msg.category_name || "-" }}
                        </span>

                    </div>

                </div>

            </div>

        </div>

        <!-- FILTER MODAL -->

        <div
            class="modal fade"
            id="messageFilterModal"
            tabindex="-1"
        >
            <div class="modal-dialog modal-dialog-centered">

                <div class="modal-content custom-modal">

                    <div class="modal-header border-0 pb-0">

                        <h5 class="modal-title fw-bold">
                            Фильтрация сообщений
                        </h5>

                        <button
                            type="button"
                            class="btn-close"
                            data-bs-dismiss="modal"
                        ></button>

                    </div>

                    <div class="modal-body">

                        <div class="mb-3">

                            <label class="form-label">
                                Категория
                            </label>

                            <select
                                class="form-select custom-input"
                                v-model="messageFilterCategory"
                            >
                                <option value="">
                                    Все категории
                                </option>

                                <option
                                    v-for="cat in messageCategories"
                                    :key="cat"
                                    :value="cat"
                                >
                                    {{ cat }}
                                </option>

                            </select>

                        </div>

                        <div class="mb-3">

                            <label class="form-label">
                                Чат
                            </label>

                            <select
                                class="form-select custom-input"
                                v-model="messageFilterChat"
                            >
                                <option value="">
                                    Все чаты
                                </option>

                                <option
                                    v-for="chat in messageChats"
                                    :key="chat"
                                    :value="chat"
                                >
                                    {{ chat }}
                                </option>

                            </select>

                        </div>

                        <div class="mb-3">

                            <label class="form-label">
                                Автор
                            </label>

                            <input
                                v-model="messageFilterAuthor"
                                type="text"
                                class="form-control custom-input"
                                placeholder="Введите имя автора"
                            />

                        </div>

                        <div class="row g-3">

                            <div class="col-6">

                                <label class="form-label">
                                    Дата с
                                </label>

                                <input
                                    v-model="messageFilterDateFrom"
                                    type="date"
                                    class="form-control custom-input"
                                />

                            </div>

                            <div class="col-6">

                                <label class="form-label">
                                    Дата по
                                </label>

                                <input
                                    v-model="messageFilterDateTo"
                                    type="date"
                                    class="form-control custom-input"
                                />

                            </div>

                            <div class="col-6">

                                <label class="form-label">
                                    Время с
                                </label>

                                <input
                                    v-model="messageFilterTimeFrom"
                                    type="time"
                                    class="form-control custom-input"
                                />

                            </div>

                            <div class="col-6">

                                <label class="form-label">
                                    Время по
                                </label>

                                <input
                                    v-model="messageFilterTimeTo"
                                    type="time"
                                    class="form-control custom-input"
                                />

                            </div>

                        </div>

                    </div>

                    <div class="modal-footer border-0 pt-0">

                        <button
                            type="button"
                            class="btn-cancel"
                            @click="resetMessageFilters"
                        >
                            Сбросить
                        </button>

                        <button
                            type="button"
                            class="btn-save"
                            data-bs-dismiss="modal"
                        >
                            Применить
                        </button>

                    </div>

                </div>

            </div>
        </div>

    </div>
</template>

<style scoped>
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
    color: #111;
}

.parser-status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border-radius: 999px;
    padding: 10px 16px;
    font-size: 14px;
    font-weight: 700;
}

.parser-status.running {
    background: rgba(25,135,84,0.12);
    color: #198754;
}

.parser-status.stopped {
    background: rgba(220,53,69,0.12);
    color: #dc3545;
}

.btn-parser {
    border: 0;
    border-radius: 14px;
    padding: 12px 18px;
    font-weight: 700;
    transition: 0.2s ease;
}

.btn-start {
    background: #198754;
    color: #fff;
}

.btn-start:hover {
    background: #157347;
}

.btn-stop {
    background: #dc3545;
    color: #fff;
}

.btn-stop:hover {
    background: #bb2d3b;
}

.btn-filter {
    border: 0;
    background: rgba(13,110,253,0.1);
    color: #0d6efd;
    border-radius: 14px;
    padding: 12px 18px;
    font-weight: 700;
    transition: 0.2s ease;
}

.btn-filter:hover {
    background: #0d6efd;
    color: #fff;
}

.message-item {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 22px;
    margin-bottom: 16px;
    border-radius: 22px;
    background: #fff;
    border: 1px solid rgba(0,0,0,0.04);
    box-shadow: 0 8px 24px rgba(15,23,42,0.05);
}

.message-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 14px;
}

.message-chat {
    font-size: 18px;
    font-weight: 800;
    color: #111;
}

.message-author {
    margin-top: 4px;
    font-size: 14px;
    color: #6c757d;
}

.message-date {
    font-size: 13px;
    color: #6c757d;
    white-space: nowrap;
}

.message-body {
    font-size: 15px;
    line-height: 1.6;
    color: #222;
    white-space: pre-wrap;
    word-break: break-word;
}

.message-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.message-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 8px 12px;
    background: #f4f7fb;
    font-size: 13px;
    font-weight: 600;
    color: #495057;
}

.empty-box {
    padding: 60px 20px;
    text-align: center;
    border-radius: 20px;
    background: #f8fafc;
    color: #6c757d;
    font-size: 16px;
}

.empty-box i {
    font-size: 38px;
}

.custom-modal {
    border: 0;
    border-radius: 24px;
    padding: 10px;
}

.custom-input {
    border-radius: 14px;
    border: 1px solid #dfe3e8;
    padding: 11px 14px;
    font-weight: 500;
    box-shadow: none !important;
}

.custom-input:focus {
    border-color: #0d6efd;
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

.btn-save {
    background: #0d6efd;
    color: #fff;
}

.custom-alert {
    border: 0;
    border-radius: 18px;
    background: rgba(220,53,69,0.1);
    color: #dc3545;
    font-weight: 600;
    padding: 14px 16px;
}

@media (max-width: 991.98px) {

    .custom-card {
        padding: 18px;
        border-radius: 20px;
    }

    .page-title {
        font-size: 22px;
    }

    .message-head {
        flex-direction: column;
    }

    .message-date {
        white-space: normal;
    }

    .btn-filter {
        width: 100%;
        justify-content: center;
    }
}
</style>