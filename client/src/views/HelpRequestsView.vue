<script setup>
import { computed, onMounted, ref } from "vue";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const success = ref("");
const requests = ref([]);
const selectedId = ref(null);
const candidates = ref([]);
const chatRoom = ref(null);
const chatText = ref("");
const chatSenderId = ref("");

const createForm = ref({
  creator_user_id: "",
  lat: "",
  lon: "",
  description: "",
  search_radius_m: 3000,
  ttl_minutes: 120,
});

const presenceForm = ref({
  user_id: "",
  lat: "",
  lon: "",
  is_available: true,
  reliability_score: 0,
});

const responseForm = ref({
  user_id: "",
  message: "",
  eta_minutes: 10,
});

const completeForm = ref({
  helper_user_id: "",
  solved: true,
  rating_delta: 2,
  rating_comment: "",
});

const filterStatus = ref("active,in_progress,waiting_confirmation,completed,canceled,expired");
const selectedRequest = computed(() => requests.value.find((row) => row.id === selectedId.value) || null);
const sortedRequests = computed(() =>
  [...requests.value].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
);

function statusClass(status) {
  if (status === "active") return "text-bg-primary";
  if (status === "in_progress" || status === "waiting_confirmation") return "text-bg-warning";
  if (status === "completed") return "text-bg-success";
  if (status === "canceled" || status === "expired") return "text-bg-danger";
  return "text-bg-secondary";
}

function pointText(location) {
  const coords = location?.coordinates || [];
  if (!Array.isArray(coords) || coords.length < 2) return "-";
  return `${Number(coords[1]).toFixed(6)}, ${Number(coords[0]).toFixed(6)}`;
}

async function loadRequests() {
  const { data } = await axios.get("/api/assistance/help-requests/", {
    params: { status: filterStatus.value },
  });
  requests.value = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
  if (!selectedId.value && requests.value.length) selectedId.value = requests.value[0].id;
}

async function reloadAll() {
  loading.value = true;
  error.value = "";
  try {
    await loadRequests();
    if (selectedId.value) {
      await Promise.all([loadCandidates(), loadChat()]);
    }
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось загрузить взаимопомощь";
  } finally {
    loading.value = false;
  }
}

async function createRequest() {
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    const { data } = await axios.post("/api/assistance/help-requests/", {
      creator_user_id: createForm.value.creator_user_id || String(auth.user?.id || ""),
      location: {
        type: "Point",
        coordinates: [Number(createForm.value.lon), Number(createForm.value.lat)],
      },
      description: createForm.value.description,
      search_radius_m: Number(createForm.value.search_radius_m || 3000),
      ttl_minutes: Number(createForm.value.ttl_minutes || 120),
    });
    selectedId.value = data.id;
    success.value = "Запрос помощи создан";
    await reloadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось создать запрос";
  } finally {
    saving.value = false;
  }
}

async function upsertPresence() {
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.post("/api/assistance/helper-presence/upsert/", {
      user_id: presenceForm.value.user_id,
      lat: Number(presenceForm.value.lat),
      lon: Number(presenceForm.value.lon),
      is_available: presenceForm.value.is_available,
      reliability_score: Number(presenceForm.value.reliability_score || 0),
    });
    success.value = "Геопозиция помощника обновлена";
    await loadCandidates();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось обновить геопозицию";
  } finally {
    saving.value = false;
  }
}

async function selectRequest(row) {
  selectedId.value = row.id;
  await Promise.all([loadCandidates(), loadChat()]);
}

async function loadCandidates() {
  candidates.value = [];
  if (!selectedId.value) return;
  try {
    const { data } = await axios.get(`/api/assistance/help-requests/${selectedId.value}/candidates/`);
    candidates.value = Array.isArray(data) ? data : [];
  } catch {
    candidates.value = [];
  }
}

async function respondToRequest(userId = "") {
  if (!selectedId.value) return;
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    const { data } = await axios.post(`/api/assistance/help-requests/${selectedId.value}/respond/`, {
      user_id: userId || responseForm.value.user_id,
      message: responseForm.value.message,
      eta_minutes: Number(responseForm.value.eta_minutes || 0),
    });
    success.value = `Отклик #${data.id} зафиксирован`;
    await reloadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось откликнуться";
  } finally {
    saving.value = false;
  }
}

async function acceptResponse(responseId) {
  if (!selectedId.value || !responseId) return;
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.post(`/api/assistance/help-requests/${selectedId.value}/accept/`, { response_id: responseId });
    success.value = "Отклик принят, чат открыт";
    await reloadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось принять отклик";
  } finally {
    saving.value = false;
  }
}

async function loadChat() {
  chatRoom.value = null;
  if (!selectedId.value) return;
  try {
    const { data } = await axios.get(`/api/assistance/help-requests/${selectedId.value}/chat/`);
    chatRoom.value = data;
    chatSenderId.value = data.creator_user_id || "";
  } catch {
    chatRoom.value = null;
    chatSenderId.value = "";
  }
}

async function sendMessage() {
  if (!selectedId.value || !chatText.value.trim()) return;
  saving.value = true;
  error.value = "";
  try {
    await axios.post(`/api/assistance/help-requests/${selectedId.value}/chat/message/`, {
      sender_user_id: chatSenderId.value,
      text: chatText.value.trim(),
    });
    chatText.value = "";
    await loadChat();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось отправить сообщение";
  } finally {
    saving.value = false;
  }
}

async function completeRequest() {
  if (!selectedId.value) return;
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.post(`/api/assistance/help-requests/${selectedId.value}/complete/`, {
      helper_user_id: completeForm.value.helper_user_id || undefined,
      solved: completeForm.value.solved,
      rating_delta: Number(completeForm.value.rating_delta || 0),
      rating_comment: completeForm.value.rating_comment,
      resolved_by_user_id: String(auth.user?.id || ""),
    });
    success.value = "Запрос завершен";
    await reloadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось завершить запрос";
  } finally {
    saving.value = false;
  }
}

onMounted(reloadAll);
</script>

<template>
  <div class="page-wrap">
    <div class="page-header mb-4">
      <div>
        <h2 class="page-title">
          <i class="bi bi-life-preserver me-2"></i>
          Взаимопомощь
        </h2>
        <div class="page-subtitle">Создание запроса, кандидаты, отклики, чат и завершение помощи</div>
      </div>
      <button class="btn-refresh" :disabled="loading" @click="reloadAll">
        <i class="bi bi-arrow-clockwise"></i>
      </button>
    </div>

    <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
    <div v-if="success" class="alert alert-success py-2">{{ success }}</div>

    <div class="flow-strip mb-4">
      <div v-for="step in 10" :key="step" class="flow-step">{{ step }}</div>
    </div>

    <div class="row g-4">
      <div class="col-xl-4">
        <div class="custom-card mb-4">
          <div class="card-title-custom">
            <i class="bi bi-plus-circle-fill me-2"></i>
            1. Создать запрос помощи
          </div>
          <form @submit.prevent="createRequest">
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label">ID инициатора</label>
                <input class="form-control custom-input" v-model="createForm.creator_user_id" :placeholder="String(auth.user?.id || '')" />
              </div>
              <div class="col-6">
                <label class="form-label">Широта</label>
                <input class="form-control custom-input" v-model="createForm.lat" required />
              </div>
              <div class="col-6">
                <label class="form-label">Долгота</label>
                <input class="form-control custom-input" v-model="createForm.lon" required />
              </div>
              <div class="col-6">
                <label class="form-label">Радиус</label>
                <input class="form-control custom-input" type="number" v-model.number="createForm.search_radius_m" />
              </div>
              <div class="col-6">
                <label class="form-label">TTL, мин</label>
                <input class="form-control custom-input" type="number" v-model.number="createForm.ttl_minutes" />
              </div>
              <div class="col-12">
                <label class="form-label">Описание</label>
                <textarea class="form-control custom-input" rows="3" v-model="createForm.description"></textarea>
              </div>
              <div class="col-12 d-grid">
                <button class="btn-create" :disabled="saving">Создать запрос</button>
              </div>
            </div>
          </form>
        </div>

        <div class="custom-card">
          <div class="card-title-custom">
            <i class="bi bi-broadcast-pin me-2"></i>
            3. Геопозиция помощника
          </div>
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label">ID помощника</label>
              <input class="form-control custom-input" v-model="presenceForm.user_id" />
            </div>
            <div class="col-6">
              <label class="form-label">Широта</label>
              <input class="form-control custom-input" v-model="presenceForm.lat" />
            </div>
            <div class="col-6">
              <label class="form-label">Долгота</label>
              <input class="form-control custom-input" v-model="presenceForm.lon" />
            </div>
            <div class="col-6">
              <label class="form-label">Надежность</label>
              <input class="form-control custom-input" type="number" step="0.1" v-model.number="presenceForm.reliability_score" />
            </div>
            <div class="col-6 d-flex align-items-end">
              <label class="flag-item"><input type="checkbox" v-model="presenceForm.is_available" /> Доступен</label>
            </div>
            <div class="col-12 d-grid">
              <button class="btn-create" :disabled="saving" @click="upsertPresence">Обновить позицию</button>
            </div>
          </div>
        </div>
      </div>

      <div class="col-xl-8">
        <div class="custom-card mb-4">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <div class="card-title-custom mb-0">
              <i class="bi bi-list-ul me-2"></i>
              Запросы помощи
            </div>
            <input class="form-control custom-input status-input" v-model="filterStatus" @change="reloadAll" />
          </div>

          <div v-if="loading" class="loading-box">Загрузка...</div>
          <div v-else-if="sortedRequests.length === 0" class="empty-box">Запросов нет</div>
          <div v-else class="request-list">
            <button
              v-for="row in sortedRequests"
              :key="row.id"
              class="request-row"
              :class="{ active: selectedId === row.id }"
              @click="selectRequest(row)"
            >
              <div>
                <div class="fw-bold">#{{ row.id }} · {{ row.event_details || "Запрос помощи" }}</div>
                <div class="text-muted small">{{ pointText(row.event_location) }} · отклики: {{ row.responses_count || 0 }}</div>
              </div>
              <span class="badge" :class="statusClass(row.status)">{{ row.status }}</span>
            </button>
          </div>
        </div>

        <div v-if="selectedRequest" class="custom-card">
          <div class="selected-head">
            <div>
              <div class="card-title-custom mb-1">Запрос #{{ selectedRequest.id }}</div>
              <div class="text-muted small">{{ selectedRequest.event_details || "Описание отсутствует" }}</div>
            </div>
            <span class="badge" :class="statusClass(selectedRequest.status)">{{ selectedRequest.status }}</span>
          </div>

          <div class="work-grid mt-3">
            <section class="work-panel">
              <div class="panel-title">4. Кандидаты</div>
              <button class="btn-action btn-edit mb-2" @click="loadCandidates">Подобрать</button>
              <div v-if="candidates.length === 0" class="mini-empty">Кандидатов пока нет</div>
              <div v-for="c in candidates" :key="c.id" class="mini-row">
                <div>
                  <b>{{ c.user_id }}</b>
                  <div class="text-muted small">{{ c.distance_m }} м</div>
                </div>
                <button class="btn-action btn-approve" @click="respondToRequest(c.user_id)">Отклик</button>
              </div>
            </section>

            <section class="work-panel">
              <div class="panel-title">5-6. Отклики</div>
              <div class="row g-2 mb-2">
                <div class="col-5"><input class="form-control custom-input" placeholder="ID помощника" v-model="responseForm.user_id" /></div>
                <div class="col-4"><input class="form-control custom-input" placeholder="ETA" type="number" v-model.number="responseForm.eta_minutes" /></div>
                <div class="col-3 d-grid"><button class="btn-action btn-edit" @click="respondToRequest()">Отклик</button></div>
                <div class="col-12"><input class="form-control custom-input" placeholder="Сообщение" v-model="responseForm.message" /></div>
              </div>
              <div v-if="!selectedRequest.responses?.length" class="mini-empty">Откликов нет</div>
              <div v-for="resp in selectedRequest.responses" :key="resp.id" class="mini-row">
                <div>
                  <b>{{ resp.responder_user_id }}</b>
                  <div class="text-muted small">{{ resp.message || "без сообщения" }}</div>
                </div>
                <button class="btn-action btn-approve" :disabled="resp.accepted" @click="acceptResponse(resp.id)">
                  {{ resp.accepted ? "Принят" : "Принять" }}
                </button>
              </div>
            </section>

            <section class="work-panel">
              <div class="panel-title">7. Чат</div>
              <div v-if="!chatRoom" class="mini-empty">Чат откроется после принятия отклика</div>
              <template v-else>
                <div class="chat-box">
                  <div v-for="msg in chatRoom.messages || []" :key="msg.id" class="chat-msg">
                    <b>{{ msg.sender_user_id }}</b>
                    <span>{{ msg.text }}</span>
                  </div>
                </div>
                <div class="d-flex gap-2 mt-2">
                  <select class="form-select custom-input chat-sender" v-model="chatSenderId">
                    <option :value="chatRoom.creator_user_id">Инициатор {{ chatRoom.creator_user_id }}</option>
                    <option :value="chatRoom.helper_user_id">Помощник {{ chatRoom.helper_user_id }}</option>
                  </select>
                  <input class="form-control custom-input" v-model="chatText" placeholder="Сообщение" />
                  <button class="btn-action btn-edit" @click="sendMessage">Отправить</button>
                </div>
              </template>
            </section>

            <section class="work-panel">
              <div class="panel-title">8-10. Завершение</div>
              <div class="row g-2">
                <div class="col-6"><input class="form-control custom-input" placeholder="ID помощника" v-model="completeForm.helper_user_id" /></div>
                <div class="col-6"><input class="form-control custom-input" type="number" v-model.number="completeForm.rating_delta" /></div>
                <div class="col-12"><input class="form-control custom-input" placeholder="Комментарий" v-model="completeForm.rating_comment" /></div>
                <div class="col-6 d-flex align-items-center"><label class="flag-item"><input type="checkbox" v-model="completeForm.solved" /> Помог</label></div>
                <div class="col-6 d-grid"><button class="btn-action btn-approve" @click="completeRequest">Завершить</button></div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-wrap {
  padding: 24px;
}
.page-header {
  background: #fff;
  border-radius: 24px;
  padding: 22px 26px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-title {
  font-weight: 800;
  margin: 0;
  color: #1f2937;
}
.page-subtitle {
  color: #7b8190;
  margin-top: 4px;
}
.custom-card {
  background: #fff;
  border-radius: 24px;
  padding: 22px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
}
.card-title-custom,
.panel-title {
  font-weight: 800;
  font-size: 18px;
}
.custom-input {
  border-radius: 14px;
  border: 1px solid #d9dee8;
  min-height: 44px;
}
.btn-create,
.btn-refresh,
.btn-action {
  border: 0;
  font-weight: 800;
}
.btn-create {
  border-radius: 14px;
  padding: 12px 22px;
  background: #0d6efd;
  color: #fff;
}
.btn-refresh {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: #edf4ff;
  color: #0d6efd;
}
.flow-strip {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 8px;
}
.flow-step {
  background: #fff;
  color: #0d6efd;
  border-radius: 14px;
  min-height: 38px;
  display: grid;
  place-items: center;
  font-weight: 900;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.05);
}
.flag-item {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  font-weight: 800;
}
.status-input {
  max-width: 420px;
}
.request-list,
.work-grid {
  display: grid;
  gap: 12px;
}
.request-row {
  width: 100%;
  border: 1px solid #edf0f4;
  border-radius: 16px;
  background: #fff;
  padding: 14px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
}
.request-row.active {
  border-color: #0d6efd;
  background: #f2f7ff;
}
.selected-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.work-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.work-panel {
  border: 1px solid #edf0f4;
  border-radius: 18px;
  padding: 14px;
}
.mini-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px;
  border-radius: 14px;
  background: #f8fafc;
  margin-top: 8px;
}
.mini-empty,
.loading-box,
.empty-box {
  border-radius: 18px;
  background: #f8fafc;
  padding: 18px;
  text-align: center;
  color: #7b8190;
}
.btn-edit {
  background: #eef5ff;
  color: #0d6efd;
  border-radius: 12px;
  padding: 10px 12px;
}
.btn-approve {
  background: #eaf7ef;
  color: #198754;
  border-radius: 12px;
  padding: 10px 12px;
}
.chat-box {
  display: grid;
  gap: 8px;
  max-height: 180px;
  overflow: auto;
  background: #f8fafc;
  border-radius: 14px;
  padding: 10px;
}
.chat-sender {
  max-width: 190px;
}
.chat-msg {
  display: grid;
  gap: 2px;
}
@media (max-width: 992px) {
  .work-grid {
    grid-template-columns: 1fr;
  }
  .flow-strip {
    grid-template-columns: repeat(5, 1fr);
  }
}
</style>
