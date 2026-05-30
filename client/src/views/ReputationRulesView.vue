<script setup>
import { computed, onMounted, ref } from "vue";
import axios from "axios";

const loading = ref(false);
const saving = ref(false);
const error = ref("");
const success = ref("");
const rules = ref([]);
const logs = ref([]);

const actionOptions = [
  { value: "event_created", label: "Создание дорожного события" },
  { value: "event_confirmed", label: "Подтверждение события" },
  { value: "event_denied", label: "Опровержение события" },
  { value: "edit_approved", label: "Правка одобрена" },
  { value: "edit_rejected", label: "Правка отклонена" },
  { value: "help_completed", label: "Помощь оказана" },
  { value: "help_failed", label: "Помощь не оказана" },
  { value: "help_canceled", label: "Помощь отменена" },
];

const form = ref({
  action: "",
  title: "",
  reputation_delta: 0,
  description: "",
  enabled: true,
});
const editForm = ref(null);

const usedActions = computed(() => new Set(rules.value.map((rule) => rule.action)));
const availableActions = computed(() => actionOptions.filter((option) => !usedActions.value.has(option.value)));
const activeRulesCount = computed(() => rules.value.filter((rule) => rule.enabled).length);
const positiveRulesCount = computed(() => rules.value.filter((rule) => Number(rule.reputation_delta) > 0).length);
const negativeRulesCount = computed(() => rules.value.filter((rule) => Number(rule.reputation_delta) < 0).length);

function normalizeRows(data) {
  return Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
}

function formatDate(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("ru-RU");
  } catch {
    return String(value);
  }
}

function actionLabel(action) {
  return actionOptions.find((option) => option.value === action)?.label || action;
}

function deltaText(delta) {
  const value = Number(delta || 0);
  return `${value > 0 ? "+" : ""}${value}`;
}

function resetForm() {
  form.value = {
    action: "",
    title: "",
    reputation_delta: 0,
    description: "",
    enabled: true,
  };
}

function fillTitleByAction() {
  if (form.value.title) return;
  form.value.title = actionLabel(form.value.action);
}

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    const [rulesRes, logsRes] = await Promise.all([
      axios.get("/api/accounts/reputation-rules/"),
      axios.get("/api/accounts/reputation/", { params: { limit: 20 } }),
    ]);
    rules.value = normalizeRows(rulesRes.data).sort((a, b) => actionLabel(a.action).localeCompare(actionLabel(b.action)));
    logs.value = normalizeRows(logsRes.data);
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось загрузить настройки рейтинга";
  } finally {
    loading.value = false;
  }
}

async function createRule() {
  if (!form.value.action) return;
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.post("/api/accounts/reputation-rules/", {
      action: form.value.action,
      title: form.value.title || actionLabel(form.value.action),
      reputation_delta: Number(form.value.reputation_delta || 0),
      description: form.value.description || "",
      enabled: form.value.enabled,
    });
    resetForm();
    success.value = "Правило добавлено";
    await loadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось добавить правило";
  } finally {
    saving.value = false;
  }
}

function startEdit(rule) {
  editForm.value = { ...rule };
}

function cancelEdit() {
  editForm.value = null;
}

async function saveRule() {
  if (!editForm.value?.id) return;
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.patch(`/api/accounts/reputation-rules/${editForm.value.id}/`, {
      title: editForm.value.title,
      reputation_delta: Number(editForm.value.reputation_delta || 0),
      description: editForm.value.description || "",
      enabled: editForm.value.enabled,
    });
    editForm.value = null;
    success.value = "Правило обновлено";
    await loadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось обновить правило";
  } finally {
    saving.value = false;
  }
}

async function toggleRule(rule) {
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.patch(`/api/accounts/reputation-rules/${rule.id}/`, {
      enabled: !rule.enabled,
    });
    success.value = !rule.enabled ? "Правило включено" : "Правило отключено";
    await loadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось изменить статус правила";
  } finally {
    saving.value = false;
  }
}

async function deleteRule(rule) {
  if (!window.confirm(`Удалить правило "${rule.title}"?`)) return;
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await axios.delete(`/api/accounts/reputation-rules/${rule.id}/`);
    success.value = "Правило удалено";
    await loadAll();
  } catch (e) {
    error.value = e?.response?.data?.detail || "Не удалось удалить правило";
  } finally {
    saving.value = false;
  }
}

onMounted(loadAll);
</script>

<template>
  <div class="page-wrap">
    <div class="page-header mb-4">
      <div>
        <h2 class="page-title">
          <i class="bi bi-stars me-2"></i>
          Рейтинг пользователей
        </h2>
        <div class="page-subtitle">Правила начисления репутации и история последних изменений</div>
      </div>
      <button class="btn-refresh" :disabled="loading" @click="loadAll">
        <i class="bi bi-arrow-clockwise"></i>
      </button>
    </div>

    <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
    <div v-if="success" class="alert alert-success py-2">{{ success }}</div>

    <div class="stats-grid mb-4">
      <div class="stat-card">
        <div class="stat-icon blue"><i class="bi bi-list-check"></i></div>
        <div>
          <div class="stat-value">{{ rules.length }}</div>
          <div class="stat-label">Всего правил</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon green"><i class="bi bi-toggle-on"></i></div>
        <div>
          <div class="stat-value">{{ activeRulesCount }}</div>
          <div class="stat-label">Активных</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon mint"><i class="bi bi-arrow-up-right"></i></div>
        <div>
          <div class="stat-value">{{ positiveRulesCount }}</div>
          <div class="stat-label">Начисляют</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon red"><i class="bi bi-arrow-down-right"></i></div>
        <div>
          <div class="stat-value">{{ negativeRulesCount }}</div>
          <div class="stat-label">Списывают</div>
        </div>
      </div>
    </div>

    <div class="custom-card mb-4">
      <div class="card-title-custom">
        <i class="bi bi-plus-circle-fill me-2"></i>
        Новое правило
      </div>

      <form @submit.prevent="createRule">
        <div class="row g-3 align-items-end">
          <div class="col-xl-3 col-lg-6">
            <label class="form-label">Действие</label>
            <select class="form-select custom-input" v-model="form.action" required @change="fillTitleByAction">
              <option value="">Выберите действие</option>
              <option v-for="option in availableActions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>
          <div class="col-xl-3 col-lg-6">
            <label class="form-label">Название</label>
            <input class="form-control custom-input" v-model="form.title" placeholder="Название правила" />
          </div>
          <div class="col-xl-2 col-lg-4">
            <label class="form-label">Баллы</label>
            <input class="form-control custom-input" type="number" v-model.number="form.reputation_delta" />
          </div>
          <div class="col-xl-3 col-lg-8">
            <label class="form-label">Описание</label>
            <input class="form-control custom-input" v-model="form.description" placeholder="Когда применяется" />
          </div>
          <div class="col-xl-1 col-lg-4 flags-row">
            <label class="flag-item"><input type="checkbox" v-model="form.enabled" /> Активно</label>
          </div>
          <div class="col-12 d-flex justify-content-end">
            <button class="btn-create" :disabled="saving || !form.action">
              <i class="bi bi-plus-lg me-2"></i>
              Добавить
            </button>
          </div>
        </div>
      </form>
    </div>

    <div class="layout-grid">
      <div class="custom-card">
        <div class="card-title-custom mb-4">
          <i class="bi bi-sliders me-2"></i>
          Правила начисления
        </div>

        <div v-if="loading" class="loading-box">Загрузка...</div>
        <div v-else-if="rules.length === 0" class="empty-box">
          <i class="bi bi-inbox me-2"></i>
          Правил пока нет
        </div>
        <div v-else class="rules-list">
          <div v-for="rule in rules" :key="rule.id" class="rule-card" :class="{ disabled: !rule.enabled }">
            <template v-if="editForm?.id === rule.id">
              <div class="rule-edit-grid">
                <div>
                  <label class="form-label">Название</label>
                  <input class="form-control custom-input" v-model="editForm.title" />
                </div>
                <div>
                  <label class="form-label">Баллы</label>
                  <input class="form-control custom-input" type="number" v-model.number="editForm.reputation_delta" />
                </div>
                <div class="wide">
                  <label class="form-label">Описание</label>
                  <input class="form-control custom-input" v-model="editForm.description" />
                </div>
                <label class="flag-item edit-flag"><input type="checkbox" v-model="editForm.enabled" /> Активно</label>
              </div>
              <div class="item-actions mt-3">
                <button class="btn-action btn-muted" :disabled="saving" @click="cancelEdit">Отмена</button>
                <button class="btn-action btn-edit" :disabled="saving" @click="saveRule">Сохранить</button>
              </div>
            </template>

            <template v-else>
              <div class="rule-main">
                <div class="rule-left">
                  <div class="rule-icon" :class="{ negative: rule.reputation_delta < 0, positive: rule.reputation_delta > 0 }">
                    <i class="bi bi-star-fill"></i>
                  </div>
                  <div class="min-w-0">
                    <div class="rule-title">{{ rule.title }}</div>
                    <div class="rule-meta">{{ actionLabel(rule.action) }} · {{ rule.action }}</div>
                    <div class="rule-description">{{ rule.description || "Описание не задано" }}</div>
                  </div>
                </div>
                <div class="rule-right">
                  <div class="delta-pill" :class="{ positive: rule.reputation_delta > 0, negative: rule.reputation_delta < 0 }">
                    {{ deltaText(rule.reputation_delta) }}
                  </div>
                  <span class="status-pill" :class="{ active: rule.enabled }">
                    {{ rule.enabled ? "Активно" : "Отключено" }}
                  </span>
                </div>
              </div>
              <div class="item-actions mt-3">
                <button class="btn-action btn-muted" :disabled="saving" @click="toggleRule(rule)">
                  <i class="bi" :class="rule.enabled ? 'bi-toggle-off' : 'bi-toggle-on'"></i>
                  {{ rule.enabled ? "Отключить" : "Включить" }}
                </button>
                <button class="btn-action btn-edit" :disabled="saving" @click="startEdit(rule)">
                  <i class="bi bi-pencil-square me-1"></i>
                  Редактировать
                </button>
                <button class="btn-action btn-delete" :disabled="saving" @click="deleteRule(rule)">
                  <i class="bi bi-trash3 me-1"></i>
                  Удалить
                </button>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div class="custom-card">
        <div class="card-title-custom mb-4">
          <i class="bi bi-clock-history me-2"></i>
          Последние начисления
        </div>

        <div v-if="loading" class="loading-box">Загрузка...</div>
        <div v-else-if="logs.length === 0" class="empty-box">Истории пока нет</div>
        <div v-else class="history-list">
          <div v-for="log in logs" :key="log.id" class="history-row">
            <div>
              <div class="history-user">{{ log.user_email || `Пользователь #${log.user}` }}</div>
              <div class="history-action">{{ actionLabel(log.action) }}</div>
              <div class="history-comment">{{ log.comment || "Без комментария" }}</div>
              <div class="history-date">{{ formatDate(log.created_at) }}</div>
            </div>
            <div class="history-delta" :class="{ positive: log.reputation_delta > 0, negative: log.reputation_delta < 0 }">
              {{ deltaText(log.reputation_delta) }}
            </div>
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
.custom-card,
.stat-card {
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
.flags-row {
  display: flex;
  align-items: center;
  gap: 14px;
}
.flag-item {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-weight: 700;
  color: #4b5563;
  white-space: nowrap;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
}
.stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-size: 20px;
}
.stat-icon.blue {
  background: #edf4ff;
  color: #0d6efd;
}
.stat-icon.green {
  background: #eaf8ef;
  color: #198754;
}
.stat-icon.mint {
  background: #e7f8f4;
  color: #0f9f86;
}
.stat-icon.red {
  background: #fff0f0;
  color: #dc3545;
}
.stat-value {
  font-size: 25px;
  font-weight: 900;
  color: #111827;
  line-height: 1;
}
.stat-label {
  color: #7b8190;
  font-weight: 700;
  margin-top: 4px;
}
.layout-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(360px, 0.6fr);
  gap: 18px;
  align-items: start;
}
.rules-list,
.history-list {
  display: grid;
  gap: 12px;
}
.rule-card,
.history-row {
  border: 1px solid #edf0f4;
  border-radius: 18px;
  padding: 16px;
}
.rule-card.disabled {
  opacity: 0.72;
}
.rule-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
.rule-left {
  display: flex;
  gap: 12px;
  min-width: 0;
}
.rule-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  background: #edf4ff;
  color: #0d6efd;
}
.rule-icon.positive {
  background: #eaf8ef;
  color: #198754;
}
.rule-icon.negative {
  background: #fff0f0;
  color: #dc3545;
}
.rule-title,
.history-user {
  font-weight: 900;
  color: #111827;
  overflow-wrap: anywhere;
}
.rule-meta,
.history-action,
.history-date {
  color: #7b8190;
  font-size: 13px;
  font-weight: 700;
}
.rule-description,
.history-comment {
  color: #4b5563;
  font-size: 14px;
  margin-top: 5px;
}
.rule-right {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: 8px;
}
.delta-pill,
.history-delta {
  min-width: 58px;
  border-radius: 999px;
  padding: 7px 12px;
  background: #eef2f7;
  color: #475569;
  text-align: center;
  font-weight: 900;
}
.delta-pill.positive,
.history-delta.positive {
  background: #eaf8ef;
  color: #198754;
}
.delta-pill.negative,
.history-delta.negative {
  background: #fff0f0;
  color: #dc3545;
}
.status-pill {
  border-radius: 999px;
  padding: 5px 10px;
  background: #f1f3f6;
  color: #7b8190;
  font-size: 12px;
  font-weight: 800;
}
.status-pill.active {
  background: #eaf8ef;
  color: #198754;
}
.item-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.btn-action {
  border-radius: 12px;
  padding: 9px 13px;
}
.btn-edit {
  background: #edf4ff;
  color: #0d6efd;
}
.btn-delete {
  background: #fff0f0;
  color: #dc3545;
}
.btn-muted {
  background: #f3f5f8;
  color: #4b5563;
}
.rule-edit-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 130px;
  gap: 12px;
  align-items: end;
}
.rule-edit-grid .wide {
  grid-column: 1 / -1;
}
.edit-flag {
  align-self: center;
}
.history-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.loading-box,
.empty-box {
  border-radius: 18px;
  padding: 22px;
  text-align: center;
  background: #f8fafc;
  color: #7b8190;
  font-weight: 700;
}
.min-w-0 {
  min-width: 0;
}
@media (max-width: 1199px) {
  .stats-grid,
  .layout-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 767px) {
  .page-wrap {
    padding: 14px;
  }
  .page-header,
  .rule-main,
  .history-row {
    flex-direction: column;
    align-items: stretch;
  }
  .rule-right {
    align-items: flex-start;
    flex-direction: row;
  }
  .rule-edit-grid {
    grid-template-columns: 1fr;
  }
}
</style>
