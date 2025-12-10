<script setup>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import Cookies from "js-cookie";

const patterns = ref([]);
const loading = ref(false);

const patternToAdd = ref({ category: "", pattern: "" });
const patternToEdit = ref({});

async function fetchPatterns() {
  loading.value = true;
  const r = await axios.get("/api/text_patterns/");
  patterns.value = r.data;
  loading.value = false;
}

async function onAddPattern() {
  await axios.post("/api/text_patterns/", {
    category: patternToAdd.value.category,
    pattern: patternToAdd.value.pattern,
  });

  patternToAdd.value = { category: "", pattern: "" };
  await fetchPatterns();
}

function onEditPatternClick(p) {
  patternToEdit.value = { ...p };
}

async function onUpdatePatternClick() {
  await axios.put(`/api/text_patterns/${patternToEdit.value.id}/`, {
    category: patternToEdit.value.category,
    pattern: patternToEdit.value.pattern,
  });

  await fetchPatterns();
}

async function onRemovePattern(p) {
  await axios.delete(`/api/text_patterns/${p.id}/`);
  await fetchPatterns();
}

onBeforeMount(async () => {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken");
  await fetchPatterns();
});
</script>

<template>
  <div class="p-3">
    <h4>Паттерны текста</h4>

    <!-- Добавление -->
    <form @submit.prevent="onAddPattern" class="mt-3">
      <div class="row g-2">

        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="patternToAdd.category" required />
            <label>Категория</label>
          </div>
        </div>

        <div class="col">
          <div class="form-floating">
            <input type="text" class="form-control" v-model="patternToAdd.pattern" required />
            <label>Регулярное выражение</label>
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
      <div v-for="p in patterns" :key="p.id" class="item-box">

        <div>
          <strong>{{ p.category }}</strong> — <code>{{ p.pattern }}</code>
        </div>

        <div class="item-actions">
          <button class="btn btn-warning" data-bs-toggle="modal" data-bs-target="#editPatternModal"
            @click="onEditPatternClick(p)">
            <i class="bi bi-pen-fill"></i>
          </button>

          <button class="btn btn-danger" @click="onRemovePattern(p)">
            <i class="bi bi-trash3-fill"></i>
          </button>
        </div>

      </div>
    </div>

    <!-- Edit modal -->
    <div class="modal fade" id="editPatternModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">

          <div class="modal-header">
            <h5 class="modal-title">Редактировать паттерн</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>

          <div class="modal-body">
            <div class="form-floating mb-2">
              <input type="text" class="form-control" v-model="patternToEdit.category" />
              <label>Категория</label>
            </div>

            <div class="form-floating">
              <input type="text" class="form-control" v-model="patternToEdit.pattern" />
              <label>Регулярное выражение</label>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
            <button class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdatePatternClick">Сохранить</button>
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
  padding: .5rem;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  margin-bottom: .5rem;
}
.item-actions {
  display: flex;
  gap: .5rem;
}
</style>