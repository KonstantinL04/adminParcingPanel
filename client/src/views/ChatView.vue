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
    <div class="page-wrap">

        <div class="page-header mb-4">
            <div>
                <h2 class="page-title">
                    <i class="bi bi-chat-dots-fill me-2"></i>
                    Телеграм-чаты
                </h2>

                <div class="page-subtitle">
                    Управление чатами для Telethon-парсера
                </div>
            </div>
        </div>

        <!-- CREATE -->

        <div class="custom-card mb-4">

            <div class="card-title-custom">
                <i class="bi bi-plus-circle-fill me-2"></i>
                Добавить чат
            </div>

            <form @submit.prevent.stop="onAddChat">

                <div class="row g-3">

                    <div class="col-xl-3 col-lg-6">
                        <label class="form-label">Название чата</label>

                        <input
                            type="text"
                            class="form-control custom-input"
                            v-model="chatToAdd.title"
                            required
                        />
                    </div>

                    <div class="col-xl-3 col-lg-6">
                        <label class="form-label">ID / username</label>

                        <input
                            type="text"
                            class="form-control custom-input"
                            v-model="chatToAdd.chat_id"
                            required
                        />
                    </div>

                    <div class="col-xl-2 col-lg-4">
                        <label class="form-label">Область</label>

                        <select
                            class="form-select custom-input"
                            v-model="chatToAdd.region"
                            @change="syncAddCities"
                        >
                            <option value="">—</option>

                            <option
                                v-for="r in regions"
                                :key="r.id"
                                :value="r.id"
                            >
                                {{ r.name }}
                            </option>
                        </select>
                    </div>

                    <div class="col-xl-2 col-lg-4">
                        <label class="form-label">Город</label>

                        <select
                            class="form-select custom-input"
                            v-model="chatToAdd.city"
                        >
                            <option value="">—</option>

                            <option
                                v-for="c in filteredCitiesAdd"
                                :key="c.id"
                                :value="c.id"
                            >
                                {{ c.name }}
                            </option>
                        </select>
                    </div>

                    <div class="col-xl-2 col-lg-4">
                        <label class="form-label">Статус</label>

                        <div class="status-switch">
                            <input
                                class="form-check-input"
                                type="checkbox"
                                id="enabledAdd"
                                v-model="chatToAdd.enabled"
                            />

                            <label
                                class="form-check-label"
                                for="enabledAdd"
                            >
                                Активен
                            </label>
                        </div>
                    </div>

                    <div class="col-12 d-flex justify-content-end">
                        <button class="btn-create">
                            <i class="bi bi-plus-lg me-2"></i>
                            Добавить чат
                        </button>
                    </div>

                </div>

            </form>

        </div>

        <!-- LIST -->

        <div class="custom-card">

            <div class="card-title-custom mb-4">
                <i class="bi bi-list-ul me-2"></i>
                Список чатов
            </div>

            <div v-if="loading" class="loading-box">
                Загрузка...
            </div>

            <div
                v-else-if="!chats.length"
                class="empty-box"
            >
                Чаты отсутствуют
            </div>

            <div
                v-else
                class="chat-grid"
            >

                <div
                    v-for="chat in chats"
                    :key="chat.id"
                    class="chat-card"
                >

                    <div class="chat-card-top">

                        <div class="chat-icon">
                            <i class="bi bi-telegram"></i>
                        </div>

                        <div
                            class="status-badge"
                            :class="chat.enabled ? 'active' : 'inactive'"
                        >
                            {{ chat.enabled ? "Активен" : "Выключен" }}
                        </div>

                    </div>

                    <div class="chat-title">
                        {{ chat.title }}
                    </div>

                    <div class="chat-id">
                        {{ chat.chat_id }}
                    </div>

                    <div class="chat-location">
                        <i class="bi bi-geo-alt me-1"></i>

                        {{ chat.region_name || "—" }}
                        /
                        {{ chat.city_name || "—" }}
                    </div>

                    <div class="chat-actions">

                        <button
                            class="btn-action btn-edit"
                            @click="onEditChatClick(chat)"
                            data-bs-toggle="modal"
                            data-bs-target="#editChatModal"
                        >
                            <i class="bi bi-pencil-square me-1"></i>
                            Редактировать
                        </button>

                        <button
                            class="btn-action btn-delete"
                            @click="onRemoveChat(chat)"
                        >
                            <i class="bi bi-trash3 me-1"></i>
                            Удалить
                        </button>

                    </div>

                </div>

            </div>

        </div>

        <!-- MODAL -->

        <div
            class="modal fade"
            id="editChatModal"
            tabindex="-1"
        >

            <div class="modal-dialog modal-dialog-centered">

                <div class="modal-content custom-modal">

                    <div class="modal-header border-0 pb-0">

                        <h5 class="modal-title fw-bold">
                            Редактирование чата
                        </h5>

                        <button
                            type="button"
                            class="btn-close"
                            data-bs-dismiss="modal"
                        ></button>

                    </div>

                    <div class="modal-body">

                        <div class="row g-3">

                            <div class="col-12">
                                <label class="form-label">
                                    Название
                                </label>

                                <input
                                    type="text"
                                    class="form-control custom-input"
                                    v-model="chatToEdit.title"
                                />
                            </div>

                            <div class="col-12">
                                <label class="form-label">
                                    ID / username
                                </label>

                                <input
                                    type="text"
                                    class="form-control custom-input"
                                    v-model="chatToEdit.chat_id"
                                />
                            </div>

                            <div class="col-md-6">
                                <label class="form-label">
                                    Область
                                </label>

                                <select
                                    class="form-select custom-input"
                                    v-model="chatToEdit.region"
                                    @change="syncEditCities"
                                >
                                    <option value="">—</option>

                                    <option
                                        v-for="r in regions"
                                        :key="r.id"
                                        :value="r.id"
                                    >
                                        {{ r.name }}
                                    </option>
                                </select>
                            </div>

                            <div class="col-md-6">
                                <label class="form-label">
                                    Город
                                </label>

                                <select
                                    class="form-select custom-input"
                                    v-model="chatToEdit.city"
                                >
                                    <option value="">—</option>

                                    <option
                                        v-for="c in filteredCitiesEdit"
                                        :key="c.id"
                                        :value="c.id"
                                    >
                                        {{ c.name }}
                                    </option>
                                </select>
                            </div>

                            <div class="col-12">

                                <div class="status-switch">
                                    <input
                                        class="form-check-input"
                                        type="checkbox"
                                        id="enabledEdit"
                                        v-model="chatToEdit.enabled"
                                    />

                                    <label
                                        class="form-check-label"
                                        for="enabledEdit"
                                    >
                                        Активен
                                    </label>
                                </div>

                            </div>

                        </div>

                    </div>

                    <div class="modal-footer border-0 pt-0">

                        <button
                            class="btn-cancel"
                            data-bs-dismiss="modal"
                        >
                            Отмена
                        </button>

                        <button
                            class="btn-save"
                            data-bs-dismiss="modal"
                            @click="onUpdateChatClick"
                        >
                            Сохранить
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
    margin-bottom: 20px;
    color: #111;
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

.status-switch {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 48px;
    padding: 0 14px;
    border-radius: 14px;
    border: 1px solid #dfe3e8;
    background: #fff;
}

.btn-create {
    border: 0;
    background: #0d6efd;
    color: #fff;
    padding: 12px 20px;
    border-radius: 14px;
    font-weight: 700;
    transition: 0.2s ease;
}

.btn-create:hover {
    background: #0b5ed7;
    transform: translateY(-1px);
}

.chat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 18px;
}

.chat-card {
    border-radius: 22px;
    padding: 20px;
    background: #fff;
    border: 1px solid #eef1f4;
    transition: 0.2s ease;
}

.chat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 28px rgba(15,23,42,0.06);
}

.chat-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
}

.chat-icon {
    width: 52px;
    height: 52px;
    border-radius: 18px;
    background: rgba(13,110,253,0.08);
    color: #0d6efd;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
}

.chat-title {
    font-size: 18px;
    font-weight: 800;
    color: #111;
    margin-bottom: 6px;
}

.chat-id {
    font-size: 14px;
    color: #6c757d;
    margin-bottom: 12px;
    word-break: break-word;
}

.chat-location {
    font-size: 14px;
    color: #495057;
    margin-bottom: 18px;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 700;
}

.status-badge.active {
    background: rgba(25,135,84,0.12);
    color: #198754;
}

.status-badge.inactive {
    background: rgba(220,53,69,0.12);
    color: #dc3545;
}

.chat-actions {
    display: flex;
    gap: 10px;
}

.btn-action {
    flex: 1;
    border: 0;
    border-radius: 14px;
    padding: 11px 14px;
    font-weight: 700;
    transition: 0.2s ease;
}

.btn-edit {
    background: rgba(13,110,253,0.1);
    color: #0d6efd;
}

.btn-edit:hover {
    background: #0d6efd;
    color: #fff;
}

.btn-delete {
    background: rgba(220,53,69,0.1);
    color: #dc3545;
}

.btn-delete:hover {
    background: #dc3545;
    color: #fff;
}

.custom-modal {
    border: 0;
    border-radius: 24px;
    padding: 10px;
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

.loading-box,
.empty-box {
    padding: 40px;
    text-align: center;
    color: #6c757d;
    border-radius: 18px;
    background: #f8fafc;
}

@media (max-width: 991.98px) {

    .custom-card {
        padding: 18px;
        border-radius: 20px;
    }

    .page-title {
        font-size: 22px;
    }

    .chat-grid {
        grid-template-columns: 1fr;
    }

    .chat-actions {
        flex-direction: column;
    }

    .btn-create {
        width: 100%;
    }
}
</style>