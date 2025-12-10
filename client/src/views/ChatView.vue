<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";
// import { useUserStore } from '@/stores/user'

// const userStore = useUserStore()

const chats = ref([]);
const loading = ref(false);
const chatToAdd = ref({ title: "", chat_id: "", enabled: true });
const chatToEdit = ref({});

async function fetchChats() {
    loading.value = true;
    const r = await axios.get("/api/chats/");
    chats.value = r.data;
    loading.value = false;
}

// Добавление чата
async function onAddChat() {
    await axios.post("/api/chats/", chatToAdd.value);
    chatToAdd.value = { title: "", chat_id: "", enabled: true };
    await fetchChats();
}

// Удаление чата
async function onRemoveChat(chat) {
    await axios.delete(`/api/chats/${chat.id}/`);
    await fetchChats();
}

// Открыть редактирование
async function onEditChatClick(chat) {
    chatToEdit.value = { ...chat };
}

// Сохранить редактирование
async function onUpdateChatClick() {
    await axios.put(`/api/chats/${chatToEdit.value.id}/`, chatToEdit.value);
    await fetchChats();
}

onBeforeMount(async () => {
    axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
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