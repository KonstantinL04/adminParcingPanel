<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";
// import { useUserStore } from '@/stores/user'

// const userStore = useUserStore()

const chats = ref([]);
const loading = ref(false);
const regions = ref([]);
const cities = ref([]);
const filteredCitiesAdd = ref([]);
const filteredCitiesEdit = ref([]);
const chatToAdd = ref({ title: "", chat_id: "", enabled: true, region: "", city: "" });
const chatToEdit = ref({});

async function fetchChats() {
    loading.value = true;
    const r = await axios.get("/api/chats/");
    chats.value = r.data;
    loading.value = false;
}

async function fetchGeoRefs() {
    const [regionsRes, citiesRes] = await Promise.all([
        axios.get("/api/regions/"),
        axios.get("/api/cities/"),
    ]);
    regions.value = regionsRes.data || [];
    cities.value = citiesRes.data || [];
    syncAddCities();
}

function syncAddCities() {
    const regionId = Number(chatToAdd.value.region);
    filteredCitiesAdd.value = Number.isFinite(regionId) && regionId
        ? cities.value.filter((c) => c.region === regionId)
        : [];
    if (!filteredCitiesAdd.value.find((c) => c.id === Number(chatToAdd.value.city))) {
        chatToAdd.value.city = "";
    }
}

function syncEditCities() {
    const regionId = Number(chatToEdit.value.region);
    filteredCitiesEdit.value = Number.isFinite(regionId) && regionId
        ? cities.value.filter((c) => c.region === regionId)
        : [];
    if (!filteredCitiesEdit.value.find((c) => c.id === Number(chatToEdit.value.city))) {
        chatToEdit.value.city = "";
    }
}

// Добавление чата
async function onAddChat() {
    await axios.post("/api/chats/", {
        ...chatToAdd.value,
        region: chatToAdd.value.region ? Number(chatToAdd.value.region) : null,
        city: chatToAdd.value.city ? Number(chatToAdd.value.city) : null,
    });
    chatToAdd.value = { title: "", chat_id: "", enabled: true, region: "", city: "" };
    filteredCitiesAdd.value = [];
    await fetchChats();
}

// Удаление чата
async function onRemoveChat(chat) {
    await axios.delete(`/api/chats/${chat.id}/`);
    await fetchChats();
}

// Открыть редактирование
async function onEditChatClick(chat) {
    chatToEdit.value = {
        ...chat,
        region: chat.region || "",
        city: chat.city || "",
    };
    syncEditCities();
}

// Сохранить редактирование
async function onUpdateChatClick() {
    await axios.put(`/api/chats/${chatToEdit.value.id}/`, {
        ...chatToEdit.value,
        region: chatToEdit.value.region ? Number(chatToEdit.value.region) : null,
        city: chatToEdit.value.city ? Number(chatToEdit.value.city) : null,
    });
    await fetchChats();
}

onBeforeMount(async () => {
    axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
    await fetchGeoRefs();
    await fetchChats();
});
</script>


<template>
    <div class="container-fluid">
        <div class="p-2">

            <div class="mb-3">
                <h4>Телеграм-чаты</h4>
            </div>

            <!-- Добавление чата -->
            <form @submit.prevent.stop="onAddChat">
                <div class="row g-2 align-items-center">
                    
                    <div class="col">
                        <div class="form-floating">
                            <input type="text"
                                   class="form-control"
                                   v-model="chatToAdd.title"
                                   required />
                            <label>Название чата</label>
                        </div>
                    </div>

                    <div class="col">
                        <div class="form-floating">
                            <input type="text"
                                   class="form-control"
                                   v-model="chatToAdd.chat_id"
                                   required />
                            <label>ID чата или username</label>
                        </div>
                    </div>

                    <div class="col-auto">
                        <div class="form-check">
                            <input class="form-check-input"
                                   type="checkbox"
                                   v-model="chatToAdd.enabled"
                                   id="enabledAdd">
                            <label class="form-check-label" for="enabledAdd">
                                Включён
                            </label>
                        </div>
                    </div>
                    <div class="col">
                        <div class="form-floating">
                            <select class="form-select" v-model="chatToAdd.region" @change="syncAddCities">
                                <option value="">—</option>
                                <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
                            </select>
                            <label>Область</label>
                        </div>
                    </div>
                    <div class="col">
                        <div class="form-floating">
                            <select class="form-select" v-model="chatToAdd.city">
                                <option value="">—</option>
                                <option v-for="c in filteredCitiesAdd" :key="c.id" :value="c.id">{{ c.name }}</option>
                            </select>
                            <label>Город</label>
                        </div>
                    </div>

                    <div class="col-auto">
                        <button class="btn btn-primary">Добавить</button>
                    </div>
                </div>
            </form>

            <!-- Список чатов -->
            <div v-if="loading" class="mt-3">Загрузка...</div>

            <div v-else class="mt-3">
                <div v-for="chat in chats" :key="chat.id" class="chat-item">
                    <div class="chat-info">
                        <div class="chat-title">{{ chat.title }}</div>
                        <div class="chat-id text-muted">{{ chat.chat_id }}</div>
                        <div class="chat-id text-muted">{{ chat.region_name || "-" }} / {{ chat.city_name || "-" }}</div>
                        <div class="chat-enabled" :class="{ off: !chat.enabled }">
                            {{ chat.enabled ? "Активен" : "Выключен" }}
                        </div>
                    </div>

                    <div class="chat-actions">
                        <button
                                class="btn btn-warning"
                                @click="onEditChatClick(chat)"
                                data-bs-toggle="modal"
                                data-bs-target="#editChatModal">
                            <i class="bi bi-pen-fill"></i>
                        </button>
                        <button
                                class="btn btn-danger"
                                @click="onRemoveChat(chat)">
                            <i class="bi bi-trash3-fill"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Модальное окно редактирования -->
        <div class="modal fade" id="editChatModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">

                    <div class="modal-header">
                        <h1 class="modal-title fs-5">Редактировать чат</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>

                    <div class="modal-body">
                        <form @submit.prevent.stop="onUpdateChatClick">

                            <div class="form-floating mb-3">
                                <input type="text" class="form-control" v-model="chatToEdit.title" required />
                                <label>Название</label>
                            </div>

                            <div class="form-floating mb-3">
                                <input type="text" class="form-control" v-model="chatToEdit.chat_id" required />
                                <label>ID чата</label>
                            </div>

                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" v-model="chatToEdit.enabled" id="enabledEdit">
                                <label class="form-check-label" for="enabledEdit">
                                    Включён
                                </label>
                            </div>

                            <div class="form-floating mb-3">
                                <select class="form-select" v-model="chatToEdit.region" @change="syncEditCities">
                                    <option value="">—</option>
                                    <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
                                </select>
                                <label>Область</label>
                            </div>

                            <div class="form-floating mb-3">
                                <select class="form-select" v-model="chatToEdit.city">
                                    <option value="">—</option>
                                    <option v-for="c in filteredCitiesEdit" :key="c.id" :value="c.id">{{ c.name }}</option>
                                </select>
                                <label>Город</label>
                            </div>
                        </form>
                    </div>

                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateChatClick">Сохранить</button>
                    </div>

                </div>
            </div>
        </div>
    </div>
</template>


<style scoped>
.chat-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: .5rem;
    margin: .5rem 0;
    border: 1px solid #ddd;
    border-radius: 8px;
}
.chat-info {
    display: flex;
    flex-direction: column;
}
.chat-title {
    font-weight: 600;
    font-size: 1.05rem;
}
.chat-id {
    font-size: .9rem;
}
.chat-enabled {
    font-size: .85rem;
    color: green;
}
.chat-enabled.off {
    color: red;
}
.chat-actions {
    display: flex;
    gap: .5rem;
}
</style>
