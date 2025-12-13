<script setup>
import axios from "axios";
import { ref, onBeforeMount, onMounted, onUnmounted } from "vue";
import Cookies from "js-cookie";

// --- СТАТУС ПАРСЕРА ---------------------------------------------------------
const parserRunning = ref(false);
let intervalId = null;

axios.defaults.withCredentials = true;
axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");

async function fetchParserStatus() {
    const r = await axios.get("/api/parser/status/");
    parserRunning.value = r.data.running;
}

async function startParser() {
    await axios.post("/api/parser/start/");
    await fetchParserStatus();
}

async function stopParser() {
    await axios.post("/api/parser/stop/");
    await fetchParserStatus();
}

onBeforeMount(async () => {
    await fetchParserStatus();
});

onMounted(() => {
    intervalId = setInterval(fetchParserStatus, 5000);
});

// --- ВЕБ-КОНСОЛЬ TELETHON ---------------------------------------------------
const consoleMessages = ref([]);
const consoleInput = ref("");
let ws = null;

function connectConsole() {
    ws = new WebSocket(`ws://6186b55170fc.ngrok-free.app/ws/parser-console/`);

    ws.onopen = () => console.log("✅ Подключение к консоли установлено");
    ws.onmessage = (event) => console.log("Сообщение из консоли:", event.data);
    ws.onclose = () => console.log("⚠ Подключение к консоли потеряно");
    ws.onerror = (err) => console.error("Ошибка WebSocket:", err);

    ws.onmessage = (event) => {
        consoleMessages.value.push(event.data);

        // автоскролл вниз
        setTimeout(() => {
            const el = document.getElementById("console-box");
            if (el) el.scrollTop = el.scrollHeight;
        }, 10);
    };

    ws.onclose = () => {
        consoleMessages.value.push("⚠ Подключение к консоли потеряно.");
    };
}

function sendConsoleInput() {
    if (!ws) return;
    ws.send(consoleInput.value);
    consoleInput.value = "";
}

function sendEnter() {
    if (ws) ws.send("");
}

onMounted(() => {
    connectConsole();
});

onUnmounted(() => {
    if (intervalId) clearInterval(intervalId);
    if (ws) ws.close();
});
</script>


<template>
    <div class="container-fluid">
        <div class="p-2">

            <!-- КНОПКИ СТАРТ/СТОП -->
            <div class="mb-4">
                <h4>Управление Telethon-парсером</h4>

                <button
                    class="btn btn-success me-2"
                    :disabled="parserRunning"
                    @click="startParser"
                >
                    ▶ Запустить парсер
                </button>

                <button
                    class="btn btn-danger"
                    :disabled="!parserRunning"
                    @click="stopParser"
                >
                    ⏹ Остановить парсер
                </button>

                <p class="mt-2">
                    <strong>Статус:</strong>
                    <span :class="parserRunning ? 'text-success' : 'text-danger'">
                        {{ parserRunning ? "Запущен" : "Остановлен" }}
                    </span>
                </p>
            </div>  

            <!-- КОНСОЛЬ -->
            <div>
                <h4>Консоль парсера</h4>

                <div id="console-box" class="console-box mb-2">
                    <pre>{{ consoleMessages.join("") }}</pre>
                </div>

                <div class="input-group">
                    <input
                        class="form-control"
                        placeholder="Введите команду..."
                        v-model="consoleInput"
                        @keyup.enter="sendConsoleInput"
                    >
                    <button class="btn btn-primary" @click="sendConsoleInput">Отправить</button>
                    <button class="btn btn-secondary" @click="sendEnter">Enter</button>
                </div>
            </div>

        </div>
    </div>
</template>


<style scoped>
.console-box {
    background: #111;
    color: #0f0;
    height: 400px;
    overflow-y: auto;
    padding: 10px;
    white-space: pre-wrap;
    border-radius: 6px;
    border: 1px solid #444;
}
</style>