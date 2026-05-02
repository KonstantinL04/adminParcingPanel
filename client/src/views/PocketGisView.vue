<script setup>
import { computed, onMounted, ref, watch } from "vue";
import axios from "axios";

const file = ref(null);
const parseError = ref("");
const isUploading = ref(false);
const isConverting = ref(false);
const isLoading = ref(false);

const sources = ref([]);
const categories = ref([]);
const regions = ref([]);
const imports = ref([]);

const selectedSource = ref("");
const selectedRegion = ref("");
const selectedCategory = ref("");
const search = ref("");

const points = ref([]);
const total = ref(0);
const limit = ref(500);
const offset = ref(0);
const pageSizeOptions = [200, 500, 1000];

const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit.value)));
async function loadSources() {
    const { data } = await axios.get("/api/events/pocketgis/sources/");
    sources.value = Array.isArray(data) ? data : [];
    if (!selectedSource.value && sources.value.length) {
        selectedSource.value = String(sources.value[0].id);
    }
}

async function loadFilters() {
    const [catResp, regResp] = await Promise.all([
        axios.get("/api/events/pocketgis/categories/"),
        axios.get("/api/regions/"),
    ]);
    categories.value = Array.isArray(catResp.data) ? catResp.data : [];
    regions.value = Array.isArray(regResp.data) ? regResp.data : [];
}

async function loadImports() {
    const { data } = await axios.get("/api/events/pocketgis/imports/");
    imports.value = Array.isArray(data) ? data.slice(0, 10) : [];
}

function onFileChange(event) {
    parseError.value = "";
    const selected = event.target.files?.[0];
    file.value = selected || null;
}

async function uploadFile() {
    if (!file.value) {
        parseError.value = "Выберите файл PocketGis.";
        return;
    }
    isUploading.value = true;
    parseError.value = "";
    try {
        const formData = new FormData();
        formData.append("file", file.value);

        await axios.post("/api/events/pocketgis/imports/upload/", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });

        file.value = null;
        const input = document.getElementById("pocketgis-file-input");
        if (input) input.value = "";
        await Promise.all([loadImports(), loadPoints(0)]);
    } catch (error) {
        parseError.value = error?.response?.data?.detail || "Ошибка импорта файла.";
    } finally {
        isUploading.value = false;
    }
}

function extractDownloadFilename(contentDisposition) {
    if (!contentDisposition) return "pocketgis_converted.csv";
    const utf8Match = contentDisposition.match(/filename\\*=UTF-8''([^;]+)/i);
    if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1]).replace(/["']/g, "");
    const plainMatch = contentDisposition.match(/filename=([^;]+)/i);
    if (plainMatch?.[1]) return plainMatch[1].trim().replace(/["']/g, "");
    return "pocketgis_converted.csv";
}

async function convertAndDownload() {
    if (!file.value) {
        parseError.value = "Выберите файл PocketGis.";
        return;
    }
    isConverting.value = true;
    parseError.value = "";
    try {
        const formData = new FormData();
        formData.append("file", file.value);
        const response = await axios.post("/api/events/pocketgis/imports/convert/", formData, {
            headers: { "Content-Type": "multipart/form-data" },
            responseType: "blob",
        });
        const blob = new Blob([response.data], { type: "text/csv;charset=utf-8;" });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = extractDownloadFilename(response.headers?.["content-disposition"]);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        parseError.value = error?.response?.data?.detail || "Ошибка конвертации файла.";
    } finally {
        isConverting.value = false;
    }
}

async function loadPoints(newOffset = offset.value) {
    isLoading.value = true;
    try {
        offset.value = Math.max(0, newOffset);
        const params = {
            limit: limit.value,
            offset: offset.value,
        };
        if (selectedSource.value) params.source = selectedSource.value;
        if (selectedRegion.value) params.region = selectedRegion.value;
        if (selectedCategory.value) params.category = selectedCategory.value;
        if (search.value.trim()) params.search = search.value.trim();

        const { data } = await axios.get("/api/events/pocketgis/points/", { params });
        points.value = Array.isArray(data?.results) ? data.results : [];
        total.value = Number(data?.count || 0);
    } catch (error) {
        parseError.value = error?.response?.data?.detail || "Ошибка загрузки данных.";
    } finally {
        isLoading.value = false;
    }
}

function nextPage() {
    if (currentPage.value >= totalPages.value) return;
    loadPoints(offset.value + limit.value);
}

function prevPage() {
    if (currentPage.value <= 1) return;
    loadPoints(offset.value - limit.value);
}

watch([selectedSource, selectedRegion, selectedCategory, limit], () => {
    loadPoints(0);
});

let searchTimer = null;
watch(search, () => {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadPoints(0), 250);
});

onMounted(async () => {
    await Promise.all([loadSources(), loadFilters(), loadImports()]);
    await loadPoints(0);
});
</script>

<template>
    <div class="container-fluid p-3">
        <h4 class="mb-3">Импорт PocketGis (OpenSpeedcam)</h4>

        <div class="card mb-3">
            <div class="card-body">
                <div class="row g-3 align-items-end">
                    <div class="col-md-4">
                        <label class="form-label">Источник</label>
                        <select class="form-select" v-model="selectedSource">
                            <option value="">Без источника</option>
                            <option v-for="s in sources" :key="s.id" :value="String(s.id)">{{ s.name }}</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Область (фильтр)</label>
                        <select class="form-select" v-model="selectedRegion">
                            <option value="">Все области</option>
                            <option v-for="r in regions" :key="r.id" :value="String(r.id)">{{ r.name }}</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Файл PocketGis</label>
                        <input id="pocketgis-file-input" class="form-control" type="file" accept=".txt,text/plain" @change="onFileChange" />
                    </div>
                </div>

                <div class="d-flex gap-2 mt-3">
                    <button class="btn btn-primary" :disabled="isUploading || !file" @click="uploadFile">
                        <span v-if="isUploading" class="spinner-border spinner-border-sm me-2"></span>
                        Импортировать
                    </button>
                    <button class="btn btn-outline-primary" :disabled="isConverting || !file" @click="convertAndDownload">
                        <span v-if="isConverting" class="spinner-border spinner-border-sm me-2"></span>
                        Сконвертировать и скачать
                    </button>
                    <router-link to="/regions-polygons" class="btn btn-outline-secondary">
                        Полигоны областей
                    </router-link>
                    <span class="text-muted align-self-center small">Импорт идет через API, данные сохраняются в БД и фильтруются по областям.</span>
                </div>
            </div>
        </div>

        <div class="alert alert-danger" v-if="parseError">{{ parseError }}</div>

        <div class="card mb-3">
            <div class="card-body">
                <div class="row g-3 align-items-end">
                    <div class="col-md-3">
                        <label class="form-label">Категория</label>
                        <select class="form-select" v-model="selectedCategory">
                            <option value="">Все категории</option>
                            <option v-for="c in categories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
                        </select>
                    </div>
                    <div class="col-md-5">
                        <label class="form-label">Поиск по деталям</label>
                        <input class="form-control" v-model="search" placeholder="Например: Кордон, Стрелка, стоп-линия" />
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Строк на странице</label>
                        <select class="form-select" v-model.number="limit">
                            <option v-for="x in pageSizeOptions" :key="x" :value="x">{{ x }}</option>
                        </select>
                    </div>
                    <div class="col-md-2 text-md-end">
                        <span class="stat-pill">Всего: {{ total }}</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="card mb-3" v-if="imports.length">
            <div class="card-header fw-semibold">Последние импорты</div>
            <div class="card-body py-2">
                <div class="small" v-for="row in imports" :key="row.id">
                    #{{ row.id }} · {{ row.file_name || "без имени" }} · {{ row.status }} · {{ row.rows_total }} строк
                    <span v-if="row.source_name"> · {{ row.source_name }}</span>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header fw-semibold d-flex justify-content-between align-items-center">
                <span>Точки PocketGis</span>
                <div class="d-flex align-items-center gap-2">
                    <button class="btn btn-outline-secondary btn-sm" :disabled="currentPage <= 1 || isLoading" @click="prevPage">Назад</button>
                    <span class="text-muted small">{{ currentPage }} / {{ totalPages }}</span>
                    <button class="btn btn-outline-secondary btn-sm" :disabled="currentPage >= totalPages || isLoading" @click="nextPage">Далее</button>
                </div>
            </div>
            <div class="table-responsive table-wrap">
                <table class="table table-sm table-striped table-hover mb-0">
                    <thead class="table-light sticky-top">
                        <tr>
                            <th>ID</th>
                            <th>Категория</th>
                            <th>Тип</th>
                            <th>Широта</th>
                            <th>Долгота</th>
                            <th>Скорость</th>
                            <th>Источник</th>
                            <th>Область</th>
                            <th>Детали</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-if="isLoading">
                            <td colspan="9" class="text-center py-3">Загрузка...</td>
                        </tr>
                        <tr v-for="row in points" :key="row.id">
                            <td>{{ row.external_idx }}</td>
                            <td>{{ row.category_name }}</td>
                            <td>{{ row.type_code }}</td>
                            <td>{{ row.location?.coordinates?.[1] }}</td>
                            <td>{{ row.location?.coordinates?.[0] }}</td>
                            <td>{{ row.speed_limit }}</td>
                            <td>{{ row.source_name || "—" }}</td>
                            <td>{{ row.region_name || "—" }}</td>
                            <td>{{ row.details || "—" }}</td>
                        </tr>
                        <tr v-if="!isLoading && points.length === 0">
                            <td colspan="9" class="text-center py-3 text-muted">Данных нет</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</template>

<style scoped>
.table-wrap {
    max-height: 65vh;
}

.stat-pill {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 999px;
    padding: 6px 12px;
    font-weight: 600;
}
</style>
