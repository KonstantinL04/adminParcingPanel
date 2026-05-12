<script setup>
import { computed, onMounted, ref } from "vue";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

const types = ref([]);
const requests = ref([]);
const historyItems = ref([]);
const selected = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");

const filterStatus = ref("active,in_progress");
const filterType = ref("");

const createForm = ref({
  type: "",
  title: "",
  description: "",
  lat: "",
  lon: "",
});

const statusForm = ref({ status: "in_progress" });
const responseForm = ref({ message: "" });
const reportForm = ref({ reason: "" });
const moderateForm = ref({ status: "rejected", reason: "" });

const currentUserId = computed(() => String(auth.user?.id || auth.user?.email || auth.user?.username || "anonymous"));
const canModerate = computed(() => !!auth.user?.is_staff || !!auth.user?.is_superuser);

async function loadTypes() {
  const { data } = await axios.get("/api/events/help-request-types/");
  types.value = Array.isArray(data) ? data : data?.results || [];
}

async function loadRequests() {
  loading.value = true;
  error.value = "";
  try {
    const params = { status: filterStatus.value };
    if (filterType.value) params.type = filterType.value;
    const { data } = await axios.get("/api/events/help-requests/", { params });
    requests.value = Array.isArray(data) ? data : data?.results || [];
  } catch (e) {
    error.value = e?.response?.data?.detail || "Ошибка загрузки заявок";
  } finally {
    loading.value = false;
  }
}

async function createRequest() {
  const lat = Number(createForm.value.lat);
  const lon = Number(createForm.value.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    error.value = "Укажите корректные координаты";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    await axios.post("/api/events/help-requests/", {
      user_id: currentUserId.value,
      type: createForm.value.type || null,
      title: createForm.value.title || "",
      description: createForm.value.description || "",
      location: { type: "Point", coordinates: [lon, lat] },
      extra_params: {},
    });
    createForm.value = { type: "", title: "", description: "", lat: "", lon: "" };
    await loadRequests();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось создать заявку";
  } finally {
    busy.value = false;
  }
}

async function openDetails(item) {
  selected.value = item;
  await loadHistory(item.id);
}

async function loadHistory(id) {
  const { data } = await axios.get(`/api/events/help-requests/${id}/history/`);
  historyItems.value = Array.isArray(data) ? data : [];
}

async function sendResponse() {
  if (!selected.value) return;
  busy.value = true;
  error.value = "";
  try {
    await axios.post(`/api/events/help-requests/${selected.value.id}/respond/`, {
      user_id: currentUserId.value,
      message: responseForm.value.message || "",
      contact_payload: {},
    });
    responseForm.value.message = "";
    await loadRequests();
    await openDetails(requests.value.find((x) => x.id === selected.value.id) || selected.value);
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось отправить отклик";
  } finally {
    busy.value = false;
  }
}

async function sendReport() {
  if (!selected.value) return;
  if (!reportForm.value.reason.trim()) return;
  busy.value = true;
  error.value = "";
  try {
    await axios.post(`/api/events/help-requests/${selected.value.id}/report/`, {
      user_id: currentUserId.value,
      reason: reportForm.value.reason.trim(),
    });
    reportForm.value.reason = "";
    await loadRequests();
    await openDetails(requests.value.find((x) => x.id === selected.value.id) || selected.value);
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось отправить жалобу";
  } finally {
    busy.value = false;
  }
}

async function changeStatus() {
  if (!selected.value) return;
  busy.value = true;
  error.value = "";
  try {
    await axios.post(`/api/events/help-requests/${selected.value.id}/status/`, {
      user_id: currentUserId.value,
      status: statusForm.value.status,
    });
    await loadRequests();
    await openDetails(requests.value.find((x) => x.id === selected.value.id) || selected.value);
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось изменить статус";
  } finally {
    busy.value = false;
  }
}

async function moderate() {
  if (!selected.value || !canModerate.value) return;
  if (!moderateForm.value.reason.trim()) {
    error.value = "Укажите причину модерации";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    await axios.post(`/api/events/help-requests/${selected.value.id}/moderate/`, {
      status: moderateForm.value.status,
      reason: moderateForm.value.reason.trim(),
    });
    moderateForm.value.reason = "";
    await loadRequests();
    await openDetails(requests.value.find((x) => x.id === selected.value.id) || selected.value);
  } catch (e) {
    error.value = e?.response?.data?.detail || "Ошибка модерации";
  } finally {
    busy.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadTypes(), loadRequests()]);
});
</script>

<template>
  <div class="container-fluid p-3">
    <h4 class="mb-3">Система взаимопомощи</h4>

    <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>

    <div class="card mb-3">
      <div class="card-body">
        <div class="row g-2">
          <div class="col-md-3">
            <label class="form-label">Тип</label>
            <select class="form-select" v-model="createForm.type">
              <option value="">Не выбрано</option>
              <option v-for="t in types" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label">Широта</label>
            <input class="form-control" v-model="createForm.lat" placeholder="52.286" />
          </div>
          <div class="col-md-3">
            <label class="form-label">Долгота</label>
            <input class="form-control" v-model="createForm.lon" placeholder="104.305" />
          </div>
          <div class="col-md-3">
            <label class="form-label">Заголовок</label>
            <input class="form-control" v-model="createForm.title" placeholder="Нужна помощь" />
          </div>
          <div class="col-12">
            <label class="form-label">Описание</label>
            <textarea class="form-control" rows="2" v-model="createForm.description" />
          </div>
        </div>
        <button class="btn btn-primary mt-3" :disabled="busy" @click="createRequest">Создать запрос</button>
      </div>
    </div>

    <div class="card mb-3">
      <div class="card-body">
        <div class="row g-2 align-items-end">
          <div class="col-md-4">
            <label class="form-label">Статусы</label>
            <input class="form-control" v-model="filterStatus" placeholder="active,in_progress" />
          </div>
          <div class="col-md-4">
            <label class="form-label">Тип (id)</label>
            <select class="form-select" v-model="filterType">
              <option value="">Все типы</option>
              <option v-for="t in types" :key="t.id" :value="String(t.id)">{{ t.name }}</option>
            </select>
          </div>
          <div class="col-md-4">
            <button class="btn btn-outline-secondary w-100" :disabled="loading" @click="loadRequests">Обновить список</button>
          </div>
        </div>
      </div>
    </div>

    <div class="card mb-3">
      <div class="card-header fw-semibold">Запросы</div>
      <div class="table-responsive">
        <table class="table table-sm table-hover mb-0">
          <thead class="table-light">
            <tr>
              <th>ID</th><th>Тип</th><th>Статус</th><th>Описание</th><th>Отклики</th><th>Жалобы</th><th>Создан</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="8" class="text-center py-3">Загрузка...</td></tr>
            <tr v-for="r in requests" :key="r.id">
              <td>{{ r.id }}</td>
              <td>{{ r.type_name || "—" }}</td>
              <td>{{ r.status }}</td>
              <td class="text-truncate-cell">{{ r.title || r.description || "—" }}</td>
              <td>{{ r.response_count }}</td>
              <td>{{ r.report_count }}</td>
              <td>{{ new Date(r.created_at).toLocaleString() }}</td>
              <td><button class="btn btn-sm btn-outline-primary" @click="openDetails(r)">Открыть</button></td>
            </tr>
            <tr v-if="!loading && requests.length === 0"><td colspan="8" class="text-center py-3 text-muted">Нет данных</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="selected" class="card">
      <div class="card-header fw-semibold">Заявка #{{ selected.id }}</div>
      <div class="card-body">
        <div class="mb-2"><b>Описание:</b> {{ selected.description || "—" }}</div>
        <div class="mb-3"><b>Статус:</b> {{ selected.status }}</div>
        <div class="row g-2">
          <div class="col-md-4">
            <label class="form-label">Сменить статус</label>
            <select class="form-select" v-model="statusForm.status">
              <option value="active">active</option>
              <option value="in_progress">in_progress</option>
              <option value="completed">completed</option>
              <option value="canceled">canceled</option>
            </select>
            <button class="btn btn-outline-primary mt-2 w-100" :disabled="busy" @click="changeStatus">Применить</button>
          </div>
          <div class="col-md-4">
            <label class="form-label">Отклик</label>
            <textarea class="form-control" rows="2" v-model="responseForm.message" />
            <button class="btn btn-outline-success mt-2 w-100" :disabled="busy" @click="sendResponse">Отправить отклик</button>
          </div>
          <div class="col-md-4">
            <label class="form-label">Жалоба</label>
            <textarea class="form-control" rows="2" v-model="reportForm.reason" />
            <button class="btn btn-outline-danger mt-2 w-100" :disabled="busy" @click="sendReport">Отправить жалобу</button>
          </div>
        </div>

        <div v-if="canModerate" class="border-top pt-3 mt-3">
          <h6>Модерация</h6>
          <div class="row g-2">
            <div class="col-md-4">
              <select class="form-select" v-model="moderateForm.status">
                <option value="rejected">rejected</option>
                <option value="archived">archived</option>
                <option value="canceled">canceled</option>
                <option value="active">active</option>
              </select>
            </div>
            <div class="col-md-6">
              <input class="form-control" v-model="moderateForm.reason" placeholder="Причина модерации" />
            </div>
            <div class="col-md-2">
              <button class="btn btn-warning w-100" :disabled="busy" @click="moderate">Применить</button>
            </div>
          </div>
        </div>

        <div class="border-top pt-3 mt-3">
          <h6>История действий</h6>
          <div class="small text-muted mb-2" v-if="historyItems.length === 0">История пуста</div>
          <div v-for="row in historyItems" :key="row.id" class="history-row">
            <span class="badge bg-light text-dark me-2">{{ row.action_type }}</span>
            <span class="me-2">{{ row.actor_user_id || "system" }}</span>
            <span class="text-muted">{{ new Date(row.created_at).toLocaleString() }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.text-truncate-cell {
  max-width: 380px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.history-row {
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
}
</style>
