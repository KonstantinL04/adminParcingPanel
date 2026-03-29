<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";

const chats = ref([]);
const selectedChat = ref("");
const loading = ref(false);
const message = ref("");

async function fetchChats() {
  const r = await axios.get("/api/chats/");
  chats.value = r.data || [];
}

async function train() {
  loading.value = true;
  message.value = "";
  try {
    const payload = selectedChat.value ? { chat_id: parseInt(selectedChat.value) } : { chat_id: "all" };
    const r = await axios.post("/api/nlp/train/", payload);
    if (r.data.status === "no_data") {
      message.value = "Нет данных для обучения по выбранному чату.";
    } else {
      message.value = "Обучение запущено.";
    }
  } catch (e) {
    message.value = "Ошибка запуска обучения.";
  } finally {
    loading.value = false;
  }
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await fetchChats();
});
</script>

<template>
  <div class="p-3">
    <h4>Дообучение NLP</h4>
    <p class="text-muted">
      Модель обучается отдельно для каждого чата на основе локаций,
      привязанных к этому чату.
    </p>

    <div class="row g-2 align-items-end">
      <div class="col-4">
        <div class="form-floating">
          <select class="form-select" v-model="selectedChat">
            <option value="">Все чаты</option>
            <option v-for="c in chats" :key="c.id" :value="c.id">{{ c.title }}</option>
          </select>
          <label>Чат</label>
        </div>
      </div>

      <div class="col-auto">
        <button class="btn btn-primary" :disabled="loading" @click="train">
          {{ loading ? "Обучение..." : "Запустить обучение" }}
        </button>
      </div>
    </div>

    <div v-if="message" class="mt-3 alert alert-info">
      {{ message }}
    </div>
  </div>
</template>
