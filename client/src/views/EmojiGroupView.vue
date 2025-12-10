<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";

const groups = ref([]);
const loading = ref(false);

const groupToAdd = ref({ category: "", emojis: "" });
const groupToEdit = ref({});

async function fetchGroups() {
  loading.value = true;
  const r = await axios.get("/api/emoji_groups/");
  groups.value = r.data;
  loading.value = false;
}

async function onAddGroup() {
  await axios.post("/api/emoji_groups/", {
    category: groupToAdd.value.category,
    emojis: groupToAdd.value.emojis.split(",").map(e => e.trim()),
  });

  groupToAdd.value = { category: "", emojis: "" };
  await fetchGroups();
}

async function onRemoveGroup(group) {
  await axios.delete(`/api/emoji_groups/${group.id}/`);
  await fetchGroups();
}

function onEditGroupClick(group) {
  groupToEdit.value = {
    ...group,
    emojis: group.emojis.join(", "),
  };
}

async function onUpdateGroupClick() {
  await axios.put(`/api/emoji_groups/${groupToEdit.value.id}/`, {
    category: groupToEdit.value.category,
    emojis: groupToEdit.value.emojis.split(",").map(e => e.trim()),
  });

  await fetchGroups();
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await fetchGroups();
});
</script>

<template>
  <div class="p-3">
    <h4>Группы эмодзи</h4>

    <!-- Добавление -->
    <form @submit.prevent="onAddGroup" class="mt-3">
      <div class="row g-2 align-items-center">

        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="groupToAdd.category" required />
            <label>Категория</label>
          </div>
        </div>

        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="groupToAdd.emojis" required />
            <label>Эмодзи (через запятую)</label>
          </div>
        </div>

        <div class="col-auto">
          <button class="btn btn-primary">Добавить</button>
        </div>

      </div>
    </form>

    <div v-if="loading" class="mt-3">Загрузка...</div>

    <!-- List -->
    <div v-else class="mt-3">
      <div v-for="g in groups" :key="g.id" class="item-box">

        <div>
          <strong>{{ g.category }}</strong> —
          <span v-for="e in g.emojis" :key="e" class="emoji-item">{{ e }}</span>
        </div>

        <div class="item-actions">
          <button class="btn btn-warning" data-bs-toggle="modal" data-bs-target="#editEmojiModal"
            @click="onEditGroupClick(g)">
            <i class="bi bi-pen-fill"></i>
          </button>

          <button class="btn btn-danger" @click="onRemoveGroup(g)">
            <i class="bi bi-trash3-fill"></i>
          </button>
        </div>

      </div>
    </div>

    <!-- Edit modal -->
    <div class="modal fade" id="editEmojiModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">

          <div class="modal-header">
            <h5 class="modal-title">Редактировать группу</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>

          <div class="modal-body">
            <div class="form-floating mb-2">
              <input type="text" class="form-control" v-model="groupToEdit.category" />
              <label>Категория</label>
            </div>

            <div class="form-floating">
              <input type="text" class="form-control" v-model="groupToEdit.emojis" />
              <label>Эмодзи (через запятую)</label>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
            <button class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateGroupClick">Сохранить</button>
          </div>

        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.item-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .5rem;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  margin-bottom: .5rem;
}
.emoji-item {
  font-size: 1.2rem;
  margin-right: .3rem;
}
.item-actions {
  display: flex;
  gap: .5rem;
}
</style>