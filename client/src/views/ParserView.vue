<script setup>
import axios from "axios";
import { ref, onMounted, onUnmounted } from "vue";
import Cookies from "js-cookie";

// --- Парсер ---
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

// --- Вкладки ---
const activeTab = ref("messages");

// --- Данные ---
const messages = ref([]);
const locations = ref([]);
const routes = ref([]);

async function fetchMessages() {
    const r = await axios.get("/api/events/messages/");
    messages.value = r.data;
}

async function fetchLocations() {
    const r = await axios.get("/api/events/locations/");
    locations.value = r.data.features || [];
}

async function fetchRoutes() {
    const r = await axios.get("/api/events/routes/");
    routes.value = r.data.features || [];
}

function fetchAll() {
    fetchMessages();
    fetchLocations();
    fetchRoutes();
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
            <button class="btn btn-success me-2" :disabled="parserRunning" @click="startParser">▶ Запустить
                парсер</button>
            <button class="btn btn-danger" :disabled="!parserRunning" @click="stopParser">⏹ Остановить парсер</button>
            <p class="mt-2">
                <strong>Статус:</strong>
                <span :class="parserRunning ? 'text-success' : 'text-danger'">
                    {{ parserRunning ? "Запущен" : "Остановлен" }}
                </span>
            </p>
        </div>

        <!-- Вкладки -->
        <ul class="nav nav-tabs mb-3">
            <li class="nav-item">
                <button class="nav-link" :class="{ active: activeTab === 'messages' }"
                    @click="activeTab = 'messages'">Сообщения</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" :class="{ active: activeTab === 'locations' }"
                    @click="activeTab = 'locations'">Местоположения</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" :class="{ active: activeTab === 'routes' }"
                    @click="activeTab = 'routes'">Маршруты</button>
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

        <div v-if="activeTab === 'locations'">
            <h5>Местоположения сообщений</h5>

            <table class="table table-striped table-bordered">
                <thead>
                    <tr>
                        <th>ID сообщения</th>
                        <th>Автор</th>
                        <th>Название места</th>
                        <th>Широта</th>
                        <th>Долгота</th>
                        <th>Источник</th>
                        <th>Confidence</th>
                    </tr>
                </thead>

                <tbody>
                    <tr v-for="loc in locations" :key="loc.id">
                        <td>{{ loc.properties.telegram_message_id }}</td>
                        <td>{{ loc.properties.author_name }}</td>
                        <td>{{ loc.properties.place_name }}</td>
                        <td>{{ loc.geometry.coordinates[1] }}</td>
                        <td>{{ loc.geometry.coordinates[0] }}</td>
                        <td>{{ loc.properties.source }}</td>
                        <td>{{ loc.properties.confidence }}</td>
                    </tr>
                </tbody>
            </table>
        </div>


        <div v-if="activeTab === 'routes'">
            <h5>Маршруты сообщений</h5>
            <table class="table table-striped table-bordered">
                <thead>
                    <tr>
                        <th>Сообщение ID</th>
                        <th>Автор</th>
                        <th>Координаты маршрута</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="route in routes" :key="route.id">
                        <td>{{ route.properties.telegram_message_id }}</td>
                        <td>{{ route.properties.author_name }}</td>
                        <td>
                            <ul>
                                <li v-for="pt in route.geometry.coordinates" :key="pt.join(',')">
                                    [{{ pt[1] }}, {{ pt[0] }}]
                                </li>
                            </ul>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

    </div>
</template>

<style scoped>
.table {
    font-size: 0.9rem;
}
</style>
