<script setup>
import { computed, onMounted, ref } from "vue";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const success = ref("");
const rows = ref([]);
const statusFilter = ref("open");
const typeFilter = ref("");
const priorityFilter = ref("");
const decisionForm = ref({});

const moderatorId = computed(() => String(auth.user?.id || ""));
const filteredRows = computed(() =>
  [...rows.value].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
);

function getDecisionForm(id) {
  if (!decisionForm.value[id]) {
    decisionForm.value[id] = {
      decision: "",
      reason: "",
    };
  }
  return decisionForm.value[id];
}

function statusClass(status) {
  if (status === "open") return "text-bg-primary";
  if (status === "in_review") return "text-bg-warning";
  if (status === "resolved") return "text-bg-success";
  if (status === "rejected") return "text-bg-danger";
  return "text-bg-secondary";
}

function typeLabel(type) {
  if (type === "event") return "Жалоба на событие";
  if (type === "event_edit") return "Правка события";
  if (type === "user") return "Жалоба на пользователя";
  return type || "-";
}

function decisionsFor(row) {
  if (row.target_type === "user") return ["warn", "restrict", "ban", "reject"];
  if (row.target_type === "event_edit") return ["confirm", "reject"];
  return ["confirm", "reject", "hide", "restore"];
}

function previewChanges(row) {
  const changes = row.event_edit_proposal?.proposed_changes;
  if (!changes) return [];
  return Object.entries(changes).map(([key, value]) => ({
    key,
    value: typeof value === "object" ? JSON.stringify(value) : String(value),
  }));
}

async function loadCases() {
  loading.value = true;
  error.value = "";
  try {
    const params = {};
    if (statusFilter.value) params.status = statusFilter.value;
    if (typeFilter.value) params.target_type = typeFilter.value;
    if (priorityFilter.value) params.priority = priorityFilter.value;
    const { data } = await axios.get("/api/moderation/cases/", { params });
    rows.value = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось загрузить кейсы модерации";
  } finally {
    loading.value = false;
  }
}

async function assignCase(row) {
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.post(`/api/moderation/cases/${row.id}/assign/`, {
      moderator_user_id: moderatorId.value,
    });
    success.value = `Кейс #${row.id} взят в работу`;
    await loadCases();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось назначить кейс";
  } finally {
    saving.value = false;
  }
}

async function resolveCase(row) {
  const form = getDecisionForm(row.id);
  if (!form.decision) {
    error.value = "Выберите решение";
    return;
  }
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.post(`/api/moderation/cases/${row.id}/resolve/`, {
      decision: form.decision,
      moderator_user_id: moderatorId.value,
      reason: form.reason || "",
    });
    success.value = `Кейс #${row.id} обработан`;
    await loadCases();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось завершить кейс";
  } finally {
    saving.value = false;
  }
}

onMounted(loadCases);
</script>

<template>
  <div class="page-wrap">
    <div class="page-header mb-4">
      <div>
        <h2 class="page-title">
          <i class="bi bi-shield-check me-2"></i>
          Модерация
        </h2>
        <div class="page-subtitle">Очередь жалоб, предложений правки и решений модератора</div>
      </div>
      <button class="btn-refresh" :disabled="loading" @click="loadCases">
        <i class="bi bi-arrow-clockwise"></i>
      </button>
    </div>

    <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
    <div v-if="success" class="alert alert-success py-2">{{ success }}</div>

    <div class="custom-card mb-4">
      <div class="card-title-custom">
        <i class="bi bi-funnel-fill me-2"></i>
        Фильтры очереди
      </div>
      <div class="row g-3 align-items-end">
        <div class="col-xl-3 col-lg-4">
          <label class="form-label">Статус</label>
          <select class="form-select custom-input" v-model="statusFilter">
            <option value="">Все</option>
            <option value="open">Открытые</option>
            <option value="in_review">В работе</option>
            <option value="resolved">Решенные</option>
            <option value="rejected">Отклоненные</option>
          </select>
        </div>
        <div class="col-xl-3 col-lg-4">
          <label class="form-label">Тип</label>
          <select class="form-select custom-input" v-model="typeFilter">
            <option value="">Все</option>
            <option value="event">Жалобы на события</option>
            <option value="event_edit">Предложения правок</option>
            <option value="user">Жалобы на пользователей</option>
          </select>
        </div>
        <div class="col-xl-3 col-lg-4">
          <label class="form-label">Приоритет</label>
          <select class="form-select custom-input" v-model="priorityFilter">
            <option value="">Все</option>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
            <option value="critical">critical</option>
          </select>
        </div>
        <div class="col-xl-3 d-grid">
          <button class="btn-create" @click="loadCases">Применить</button>
        </div>
      </div>
    </div>

    <div class="custom-card">
      <div class="card-title-custom mb-4">
        <i class="bi bi-list-check me-2"></i>
        Кейсы
      </div>

      <div v-if="loading" class="loading-box">Загрузка...</div>
      <div v-else-if="filteredRows.length === 0" class="empty-box">
        <i class="bi bi-inbox me-2"></i>
        Кейсов нет
      </div>

      <div v-else class="case-grid">
        <div v-for="row in filteredRows" :key="row.id" class="case-card">
          <div class="case-head">
            <div>
              <div class="case-title">#{{ row.id }} · {{ typeLabel(row.target_type) }}</div>
              <div class="case-subtitle">Объект: {{ row.target_id }} · Открыл: {{ row.opened_by_user_id || "-" }}</div>
            </div>
            <div class="case-badges">
              <span class="badge" :class="statusClass(row.status)">{{ row.status }}</span>
              <span class="badge text-bg-light">{{ row.priority }}</span>
            </div>
          </div>

          <div class="case-body">
            <div class="reason-box">{{ row.reason || "Описание отсутствует" }}</div>

            <div v-if="row.reports?.length" class="mini-section">
              <div class="mini-title">Жалобы</div>
              <div v-for="report in row.reports" :key="report.id" class="mini-row">
                <b>{{ report.reporter_user_id }}</b>
                <span>{{ report.text || "без текста" }}</span>
              </div>
            </div>

            <div v-if="row.event_edit_proposal" class="mini-section">
              <div class="mini-title">Предлагаемые изменения</div>
              <div v-for="change in previewChanges(row)" :key="change.key" class="change-row">
                <span>{{ change.key }}</span>
                <b>{{ change.value }}</b>
              </div>
            </div>
          </div>

          <div class="case-actions">
            <button class="btn-action btn-edit" :disabled="saving" @click="assignCase(row)">
              <i class="bi bi-person-check me-1"></i>
              Взять
            </button>
            <select class="form-select custom-input decision-select" v-model="getDecisionForm(row.id).decision">
              <option value="">Решение</option>
              <option v-for="decision in decisionsFor(row)" :key="decision" :value="decision">{{ decision }}</option>
            </select>
            <input class="form-control custom-input reason-input" v-model="getDecisionForm(row.id).reason" placeholder="Причина решения" />
            <button class="btn-action btn-approve" :disabled="saving" @click="resolveCase(row)">
              <i class="bi bi-check-lg me-1"></i>
              OK
            </button>
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
  align-items: center;
  justify-content: space-between;
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
.card-title-custom {
  font-weight: 800;
  font-size: 18px;
  margin-bottom: 18px;
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
.case-grid {
  display: grid;
  gap: 14px;
}
.case-card {
  border: 1px solid #edf0f4;
  border-radius: 18px;
  padding: 16px;
}
.case-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.case-title {
  font-weight: 800;
  color: #1f2937;
}
.case-subtitle {
  color: #7b8190;
  font-size: 13px;
}
.case-badges,
.case-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.case-body {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}
.reason-box {
  background: #f8fafc;
  border-radius: 14px;
  padding: 12px;
  color: #334155;
}
.mini-section {
  border-top: 1px solid #edf0f4;
  padding-top: 10px;
}
.mini-title {
  font-weight: 800;
  margin-bottom: 8px;
}
.mini-row,
.change-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-radius: 12px;
  background: #f8fafc;
  padding: 8px 10px;
  margin-bottom: 6px;
}
.case-actions {
  margin-top: 14px;
}
.decision-select {
  max-width: 180px;
}
.reason-input {
  min-width: 240px;
  flex: 1;
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
  padding: 10px 14px;
}
.loading-box,
.empty-box {
  border-radius: 18px;
  background: #f8fafc;
  padding: 28px;
  text-align: center;
  color: #7b8190;
}
@media (max-width: 768px) {
  .case-head,
  .mini-row,
  .change-row {
    flex-direction: column;
  }
  .decision-select,
  .reason-input {
    max-width: none;
    width: 100%;
  }
}
</style>
