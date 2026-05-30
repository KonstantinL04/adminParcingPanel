<!-- PocketGis.vue — полный код -->
<script setup>
import { computed, onMounted, ref, watch } from "vue";
import axios from "axios";

const file = ref(null);
const parseError = ref("");
const isUploading = ref(false);
const isConverting = ref(false);
const isLoading = ref(false);

const sources = ref([]);
const regions = ref([]);
const imports = ref([]);
const catalogItems = ref([]);

const selectedSource = ref("");
const selectedRegion = ref("");
const search = ref("");

const showMappingModal = ref(false);
const detectedCategories = ref([]);
const categoryMapping = ref({});

const points = ref([]);
const total = ref(0);
const limit = ref(500);
const offset = ref(0);
const pageSizeOptions = [200, 500, 1000];

const showSourceDropdown = ref(false);
const showRegionDropdown = ref(false);
const showLimitDropdown = ref(false);

const sourceDropdown = ref(null);
const regionDropdown = ref(null);
const limitDropdown = ref(null);

const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit.value)));

const selectedSourceName = computed(() => {
    if (!selectedSource.value) return "Без источника";
    const source = sources.value.find(s => String(s.id) === selectedSource.value);
    return source ? source.name : "Без источника";
});

const selectedRegionName = computed(() => {
    if (!selectedRegion.value) return "Все области";
    const region = regions.value.find(r => String(r.id) === selectedRegion.value);
    return region ? region.name : "Все области";
});

const selectedLimitName = computed(() => limit.value);

async function loadSources() {
    const { data } = await axios.get("/api/events/pocketgis/sources/");
    sources.value = Array.isArray(data) ? data : [];
    if (!selectedSource.value && sources.value.length) {
        selectedSource.value = String(sources.value[0].id);
    }
}

async function loadRegions() {
    const { data } = await axios.get("/api/regions/");
    regions.value = Array.isArray(data) ? data : [];
}

async function loadCatalog() {
    try {
        const { data } = await axios.get("/api/events/event-classes/catalog/");
        const items = [];
        for (const cls of data) {
            if (cls.items) {
                for (const item of cls.items) {
                    if (item.source_kind === "static") {
                        items.push({ ...item, _className: cls.name });
                    }
                }
            }
        }
        catalogItems.value = items;
    } catch (e) {
        console.error("Ошибка загрузки каталога:", e);
    }
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

function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
        const char = line[i];

        if (char === '"') {
            if (inQuotes && i + 1 < line.length && line[i + 1] === '"') {
                current += '"';
                i++;
            } else {
                inQuotes = !inQuotes;
            }
        } else if (char === ';' && !inQuotes) {
            result.push(current.trim());
            current = '';
        } else {
            current += char;
        }
    }
    result.push(current.trim());
    return result;
}

async function analyzeFile() {
    if (!file.value) {
        parseError.value = "Выберите файл PocketGis.";
        return;
    }

    isUploading.value = true;
    parseError.value = "";

    try {
        const formData = new FormData();
        formData.append("file", file.value);

        const response = await axios.post("/api/events/pocketgis/imports/convert/", formData, {
            headers: { "Content-Type": "multipart/form-data" },
            responseType: "text",
        });

        const text = response.data;
        const lines = text.split('\n').slice(1);
        const categories = new Set();

        for (const line of lines) {
            if (!line.trim()) continue;
            const parts = parseCSVLine(line);
            if (parts.length >= 5) {
                const cat = parts[4].trim();
                if (cat) categories.add(cat);
            }
        }

        detectedCategories.value = Array.from(categories).sort();
        
        // Сброс маппинга — пользователь сопоставит вручную
        const mapping = {};
        for (const cat of detectedCategories.value) {
            mapping[cat] = null;
        }
        categoryMapping.value = mapping;
        showMappingModal.value = true;

    } catch (error) {
        parseError.value = error?.response?.data?.detail || "Ошибка анализа файла.";
    } finally {
        isUploading.value = false;
    }
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

        if (selectedSource.value) {
            formData.append("source_id", selectedSource.value);
        }

        formData.append("category_mapping", JSON.stringify(categoryMapping.value));

        await axios.post("/api/events/events/import/", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });

        file.value = null;
        const input = document.getElementById("pocketgis-file-input");
        if (input) input.value = "";

        showMappingModal.value = false;
        detectedCategories.value = [];
        categoryMapping.value = {};

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
            source_kind: "static",
        };
        if (selectedRegion.value) params.region = selectedRegion.value;
        if (search.value.trim()) params.search = search.value.trim();

        const { data } = await axios.get("/api/events/events/", { params });
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

function toggleSourceDropdown() {
    showSourceDropdown.value = !showSourceDropdown.value;
    showRegionDropdown.value = false;
    showLimitDropdown.value = false;
}

function toggleRegionDropdown() {
    showRegionDropdown.value = !showRegionDropdown.value;
    showSourceDropdown.value = false;
    showLimitDropdown.value = false;
}

function toggleLimitDropdown() {
    showLimitDropdown.value = !showLimitDropdown.value;
    showSourceDropdown.value = false;
    showRegionDropdown.value = false;
}

function selectSource(id) {
    selectedSource.value = id;
    showSourceDropdown.value = false;
}

function selectRegion(id) {
    selectedRegion.value = id;
    showRegionDropdown.value = false;
}

function selectLimit(value) {
    limit.value = value;
    showLimitDropdown.value = false;
}

function closeMappingModal() {
    showMappingModal.value = false;
}

function handleClickOutside(event) {
    if (sourceDropdown.value && !sourceDropdown.value.contains(event.target)) {
        showSourceDropdown.value = false;
    }
    if (regionDropdown.value && !regionDropdown.value.contains(event.target)) {
        showRegionDropdown.value = false;
    }
    if (limitDropdown.value && !limitDropdown.value.contains(event.target)) {
        showLimitDropdown.value = false;
    }
}

watch([selectedSource, selectedRegion, limit], () => {
    loadPoints(0);
});

let searchTimer = null;
watch(search, () => {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadPoints(0), 250);
});

onMounted(async () => {
    document.addEventListener('click', handleClickOutside);
    await Promise.all([loadSources(), loadRegions(), loadImports(), loadCatalog()]);
    await loadPoints(0);
});
</script>

<template>
    <div class="page-wrap">

        <!-- HEADER -->
        <div class="page-header mb-4">
            <div>
                <h2 class="page-title">
                    <i class="bi bi-upload me-2"></i>
                    Импорт PocketGis
                </h2>
                <div class="page-subtitle">
                    OpenSpeedcam — импорт и управление точками
                </div>
            </div>
        </div>

        <!-- UPLOAD CARD -->
        <div class="custom-card mb-4">
            <div class="card-title-custom">
                <i class="bi bi-cloud-upload-fill me-2"></i>
                Загрузка файла
            </div>

            <div class="row g-3 align-items-end">
                <div class="col-lg-4">
                    <label class="form-label">Источник</label>
                    <div class="main-dropdown" ref="sourceDropdown">
                        <button
                            class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
                            type="button" @click="toggleSourceDropdown">
                            <span :class="{ 'text-muted': !selectedSource }">{{ selectedSourceName }}</span>
                            <i class="bi bi-chevron-down ms-2"></i>
                        </button>
                        <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: showSourceDropdown }">
                            <div class="dropdown-items-scroll">
                                <button class="dropdown-item-custom" :class="{ active: !selectedSource }"
                                    @click="selectSource('')">
                                    <i class="bi bi-x-circle me-2"></i>
                                    Без источника
                                </button>
                                <button v-for="s in sources" :key="s.id" class="dropdown-item-custom"
                                    :class="{ active: selectedSource === String(s.id) }"
                                    @click="selectSource(String(s.id))">
                                    {{ s.name }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4">
                    <label class="form-label">Область (фильтр)</label>
                    <div class="main-dropdown" ref="regionDropdown">
                        <button
                            class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
                            type="button" @click="toggleRegionDropdown">
                            <span :class="{ 'text-muted': !selectedRegion }">{{ selectedRegionName }}</span>
                            <i class="bi bi-chevron-down ms-2"></i>
                        </button>
                        <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: showRegionDropdown }">
                            <div class="dropdown-items-scroll">
                                <button class="dropdown-item-custom" :class="{ active: !selectedRegion }"
                                    @click="selectRegion('')">
                                    <i class="bi bi-globe me-2"></i>
                                    Все области
                                </button>
                                <button v-for="r in regions" :key="r.id" class="dropdown-item-custom"
                                    :class="{ active: selectedRegion === String(r.id) }"
                                    @click="selectRegion(String(r.id))">
                                    {{ r.name }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4">
                    <label class="form-label">Файл PocketGis</label>
                    <div class="file-upload-wrapper">
                        <input id="pocketgis-file-input" class="form-control custom-input file-input-hidden" type="file"
                            accept=".txt,.csv,text/plain,text/csv" @change="onFileChange" />
                        <label for="pocketgis-file-input" class="file-upload-label">
                            <i class="bi bi-file-earmark-text me-2"></i>
                            <span v-if="file">{{ file.name }}</span>
                            <span v-else class="text-muted">Выберите файл .txt или .csv</span>
                        </label>
                    </div>
                </div>
            </div>

            <div class="d-flex gap-2 mt-3 flex-wrap">
                <button class="btn-create" :disabled="isUploading || !file" @click="analyzeFile">
                    <span v-if="isUploading" class="spinner-border spinner-border-sm me-2"></span>
                    <i class="bi bi-search me-2"></i>
                    Анализировать
                </button>
                <button class="btn-convert" :disabled="isConverting || !file" @click="convertAndDownload">
                    <span v-if="isConverting" class="spinner-border spinner-border-sm me-2"></span>
                    <i class="bi bi-arrow-repeat me-2"></i>
                    Сконвертировать и скачать
                </button>
                <router-link to="/regions-polygons" class="btn-outline">
                    <i class="bi bi-bounding-box me-2"></i>
                    Области и города
                </router-link>
            </div>

            <div class="info-text mt-2">
                <i class="bi bi-info-circle me-1"></i>
                Поддерживаются файлы .txt (TSV) и .csv. Нажмите &laquo;Анализировать&raquo; чтобы сопоставить категории
            </div>
        </div>

        <!-- ERROR ALERT -->
        <div v-if="parseError" class="error-card mb-4">
            <div class="d-flex align-items-center gap-2">
                <i class="bi bi-exclamation-triangle-fill"></i>
                <span>{{ parseError }}</span>
            </div>
        </div>

        <!-- FILTERS CARD -->
        <div class="custom-card mb-4">
            <div class="card-title-custom">
                <i class="bi bi-funnel-fill me-2"></i>
                Фильтры и поиск
            </div>

            <div class="row g-3 align-items-end">
                <div class="col-lg-5">
                    <label class="form-label">Поиск по деталям</label>
                    <input class="form-control custom-input" v-model="search"
                        placeholder="Кордон, Стрелка, стоп-линия..." />
                </div>
                <div class="col-md-3 col-lg-2">
                    <label class="form-label">Строк на странице</label>
                    <div class="main-dropdown" ref="limitDropdown">
                        <button
                            class="form-control custom-input text-start d-flex justify-content-between align-items-center dropdown-toggle-btn"
                            type="button" @click="toggleLimitDropdown">
                            <span>{{ selectedLimitName }}</span>
                            <i class="bi bi-chevron-down ms-2"></i>
                        </button>
                        <div class="dropdown-menu custom-menu shadow border-0" :class="{ show: showLimitDropdown }">
                            <div class="dropdown-items-scroll">
                                <button v-for="x in pageSizeOptions" :key="x" class="dropdown-item-custom"
                                    :class="{ active: limit === x }" @click="selectLimit(x)">
                                    {{ x }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 col-lg-2">
                    <div class="stat-badge">
                        <i class="bi bi-database me-2"></i>
                        Всего: {{ total }}
                    </div>
                </div>
            </div>
        </div>

        <!-- IMPORTS HISTORY -->
        <div v-if="imports.length" class="custom-card mb-4">
            <div class="card-title-custom mb-3">
                <i class="bi bi-clock-history me-2"></i>
                Последние импорты
            </div>
            <div class="imports-list">
                <div v-for="row in imports" :key="row.id" class="import-item">
                    <div class="import-id">#{{ row.id }}</div>
                    <div class="import-name">{{ row.file_name || "без имени" }}</div>
                    <div class="import-badge" :class="'status-' + row.status">
                        {{ row.status }}
                    </div>
                    <div class="import-rows">{{ row.rows_total }} строк</div>
                    <div v-if="row.source_name" class="import-source">{{ row.source_name }}</div>
                </div>
            </div>
        </div>

        <!-- TABLE CARD -->
        <div class="custom-card">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div class="card-title-custom mb-0">
                    <i class="bi bi-pin-map-fill me-2"></i>
                    Точки PocketGis
                </div>
                <div class="pagination-controls">
                    <button class="btn-page" :disabled="currentPage <= 1 || isLoading" @click="prevPage">
                        <i class="bi bi-chevron-left"></i>
                    </button>
                    <span class="page-indicator">{{ currentPage }} / {{ totalPages }}</span>
                    <button class="btn-page" :disabled="currentPage >= totalPages || isLoading" @click="nextPage">
                        <i class="bi bi-chevron-right"></i>
                    </button>
                </div>
            </div>

            <div class="table-responsive">
                <table class="custom-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Категория</th>
                            <th>Широта</th>
                            <th>Долгота</th>
                            <th>Скорость</th>
                            <th>Источник</th>
                            <th>Детали</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-if="isLoading">
                            <td colspan="7" class="text-center py-4">
                                <div class="loading-box">
                                    <span class="spinner-border spinner-border-sm me-2"></span>
                                    Загрузка...
                                </div>
                            </td>
                        </tr>
                        <tr v-for="row in points" :key="row.id">
                            <td class="fw-semibold">{{ row.external_idx }}</td>
                            <td>
                                <span class="category-badge">{{ row.category_name || row.class_item }}</span>
                            </td>
                            <td class="text-monospace">{{ row.location?.coordinates?.[1] }}</td>
                            <td class="text-monospace">{{ row.location?.coordinates?.[0] }}</td>
                            <td>
                                <span class="speed-badge" v-if="row.speed_limit">
                                    {{ row.speed_limit }} км/ч
                                </span>
                                <span v-else>—</span>
                            </td>
                            <td>{{ row.source_name || "—" }}</td>
                            <td class="details-cell">{{ row.details || "—" }}</td>
                        </tr>
                        <tr v-if="!isLoading && points.length === 0">
                            <td colspan="7" class="text-center py-5">
                                <div class="empty-box">
                                    <i class="bi bi-inbox me-2"></i>
                                    Данных нет
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- MAPPING MODAL -->
    <transition name="fade">
        <div v-if="showMappingModal" class="modal-overlay" @click.self="closeMappingModal">
            <div class="modal-dialog-custom">
                <div class="mapping-modal-card">
                    <div class="modal-header-custom">
                        <h5 class="modal-title-custom">
                            Сопоставление категорий
                            <span class="badge-count">{{ detectedCategories.length }}</span>
                        </h5>
                        <button type="button" class="btn-close-custom" @click="closeMappingModal">×</button>
                    </div>
                    <div class="modal-body-custom">
                        <div class="mapping-info">
                            <i class="bi bi-info-circle me-2"></i>
                            Для каждой категории из файла выберите соответствующий элемент из каталога.
                        </div>
                        <div class="mapping-list">
                            <div v-for="cat in detectedCategories" :key="cat" class="mapping-item">
                                <div class="mapping-source">{{ cat }}</div>
                                <i class="bi bi-arrow-right text-muted mx-2"></i>
                                <select 
                                    class="form-select mapping-select" 
                                    v-model="categoryMapping[cat]"
                                    :class="{ 'mapped': categoryMapping[cat], 'unmapped': !categoryMapping[cat] }"
                                >
                                    <option :value="null">— Пропустить —</option>
                                    <optgroup 
                                        v-for="cls in [...new Set(catalogItems.map(i => i._className))]" 
                                        :key="cls" 
                                        :label="cls"
                                    >
                                        <option 
                                            v-for="item in catalogItems.filter(i => i._className === cls)" 
                                            :key="item.id" 
                                            :value="item.id"
                                        >
                                            {{ item.name }}
                                        </option>
                                    </optgroup>
                                </select>
                            </div>
                        </div>
                        <div class="mapping-summary mt-3">
                            Сопоставлено: {{ Object.values(categoryMapping).filter(v => v).length }} из {{ detectedCategories.length }}
                        </div>
                    </div>
                    <div class="modal-footer-custom">
                        <button class="btn-cancel" @click="closeMappingModal">Отмена</button>
                        <button class="btn-save" @click="uploadFile" :disabled="isUploading">
                            <span v-if="isUploading" class="spinner-border spinner-border-sm me-2"></span>
                            Импортировать
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </transition>
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
    background: rgba(255, 255, 255, 0.92);
    backdrop-filter: blur(12px);
    border-radius: 24px;
    padding: 24px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
    border: 1px solid rgba(0, 0, 0, 0.04);
    position: relative;
    z-index: 1;
}

.custom-card:has(.custom-menu.show) {
    z-index: 50;
    overflow: visible;
}

.card-title-custom {
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 18px;
    color: #111;
}

.custom-input {
    border-radius: 14px;
    border: 1px solid #dfe3e8;
    padding: 12px 14px;
    font-weight: 500;
    box-shadow: none !important;
    background: #fff;
}

.custom-input:focus {
    border-color: #0d6efd;
}

.btn-create {
    border: 0;
    background: #0d6efd;
    color: #fff;
    padding: 12px 20px;
    border-radius: 14px;
    font-weight: 700;
    transition: 0.2s ease;
    display: inline-flex;
    align-items: center;
}

.btn-create:hover:not(:disabled) {
    background: #0b5ed7;
    transform: translateY(-1px);
}

.btn-create:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
}

.btn-convert {
    border: 0;
    background: rgba(13, 110, 253, 0.1);
    color: #0d6efd;
    padding: 12px 20px;
    border-radius: 14px;
    font-weight: 700;
    transition: 0.2s ease;
    display: inline-flex;
    align-items: center;
}

.btn-convert:hover:not(:disabled) {
    background: rgba(13, 110, 253, 0.2);
    transform: translateY(-1px);
}

.btn-convert:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
}

.btn-outline {
    border: 0;
    background: rgba(13, 110, 253, 0.1);
    color: #0d6efd;
    padding: 12px 20px;
    border-radius: 14px;
    font-weight: 700;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    transition: 0.2s ease;
}

.btn-outline:hover {
    background: rgba(13, 110, 253, 0.2);
    transform: translateY(-1px);
}

.main-dropdown {
    position: relative;
    z-index: 100;
}

.main-dropdown:has(.custom-menu.show) {
    z-index: 1060;
}

.dropdown-toggle-btn {
    cursor: pointer;
    user-select: none;
    background: #fff;
    transition: all 0.2s ease;
    position: relative;
    z-index: 1;
}

.dropdown-toggle-btn:hover {
    border-color: #0d6efd;
}

.custom-menu {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    min-width: 100%;
    max-height: 320px;
    padding: 8px;
    border-radius: 18px;
    background: #fff;
    box-shadow: 0 12px 40px rgba(15, 23, 42, 0.15), 0 4px 12px rgba(15, 23, 42, 0.08);
    opacity: 0;
    visibility: hidden;
    transform: translateY(-8px);
    display: block;
    pointer-events: none;
    transition: opacity 0.2s ease, visibility 0.2s ease, transform 0.2s ease;
    z-index: 1060;
}

.main-dropdown .custom-menu.show {
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
    transform: translateY(0);
}

.dropdown-items-scroll {
    max-height: 280px;
    overflow-y: auto;
}

.dropdown-item-custom {
    display: flex;
    align-items: center;
    width: 100%;
    border: 0;
    background: transparent;
    border-radius: 12px;
    padding: 11px 14px;
    font-weight: 600;
    font-size: 14px;
    color: #111;
    transition: all 0.18s ease;
    cursor: pointer;
    text-align: left;
    margin-bottom: 2px;
}

.dropdown-item-custom:hover {
    background: #f0f4ff;
    transform: translateX(2px);
}

.dropdown-item-custom.active {
    background: rgba(13, 110, 253, 0.08);
    color: #0d6efd;
}

.dropdown-items-scroll::-webkit-scrollbar {
    width: 5px;
}

.dropdown-items-scroll::-webkit-scrollbar-track {
    background: transparent;
}

.dropdown-items-scroll::-webkit-scrollbar-thumb {
    background: #dfe3e8;
    border-radius: 3px;
}

.dropdown-items-scroll::-webkit-scrollbar-thumb:hover {
    background: #c1c7cd;
}

.file-upload-wrapper {
    position: relative;
}

.file-input-hidden {
    position: absolute;
    opacity: 0;
    width: 100%;
    height: 100%;
    cursor: pointer;
    z-index: 2;
}

.file-upload-label {
    display: flex;
    align-items: center;
    padding: 12px 14px;
    border-radius: 14px;
    border: 1px solid #dfe3e8;
    background: #fff;
    cursor: pointer;
    font-weight: 500;
    transition: 0.2s ease;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.file-upload-label:hover {
    border-color: #0d6efd;
}

.info-text {
    color: #6c757d;
    font-size: 13px;
    font-weight: 500;
}

.error-card {
    background: rgba(220, 53, 69, 0.08);
    border: 1px solid rgba(220, 53, 69, 0.2);
    border-radius: 16px;
    padding: 14px 18px;
    color: #dc3545;
    font-weight: 600;
    font-size: 14px;
}

.stat-badge {
    display: inline-flex;
    align-items: center;
    background: rgba(13, 110, 253, 0.1);
    color: #0d6efd;
    padding: 10px 16px;
    border-radius: 14px;
    font-weight: 700;
    font-size: 14px;
    white-space: nowrap;
}

.imports-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.import-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 14px;
    background: #f8fafc;
    border: 1px solid #eef1f4;
    font-size: 13px;
    font-weight: 500;
    flex-wrap: wrap;
}

.import-id {
    font-weight: 700;
    color: #0d6efd;
    min-width: 40px;
}

.import-name {
    font-weight: 600;
    color: #111;
    flex: 1;
    min-width: 120px;
}

.import-badge {
    padding: 4px 10px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
}

.status-success {
    background: rgba(25, 135, 84, 0.1);
    color: #198754;
}

.status-error {
    background: rgba(220, 53, 69, 0.1);
    color: #dc3545;
}

.status-processing {
    background: rgba(255, 193, 7, 0.1);
    color: #ffc107;
}

.import-rows {
    color: #6c757d;
}

.import-source {
    color: #6c757d;
    font-style: italic;
}

.pagination-controls {
    display: flex;
    align-items: center;
    gap: 12px;
}

.btn-page {
    width: 36px;
    height: 36px;
    border: 0;
    background: rgba(13, 110, 253, 0.1);
    color: #0d6efd;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    font-weight: 700;
    transition: 0.2s ease;
    cursor: pointer;
}

.btn-page:hover:not(:disabled) {
    background: #0d6efd;
    color: #fff;
}

.btn-page:disabled {
    opacity: 0.3;
    cursor: not-allowed;
}

.page-indicator {
    font-weight: 700;
    color: #111;
    font-size: 14px;
    min-width: 60px;
    text-align: center;
}

.table-responsive {
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid #eef1f4;
}

.custom-table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
}

.custom-table thead {
    background: #f8fafc;
    border-bottom: 2px solid #eef1f4;
}

.custom-table th {
    padding: 14px 16px;
    font-size: 13px;
    font-weight: 700;
    color: #6c757d;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    text-align: left;
    white-space: nowrap;
}

.custom-table tbody tr {
    border-bottom: 1px solid #f0f2f5;
    transition: 0.15s ease;
}

.custom-table tbody tr:hover {
    background: #f8fafc;
}

.custom-table td {
    padding: 14px 16px;
    font-size: 14px;
    font-weight: 500;
    color: #111;
    vertical-align: middle;
}

.text-monospace {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    color: #0d6efd;
}

.category-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 10px;
    background: rgba(13, 110, 253, 0.08);
    color: #0d6efd;
    font-weight: 600;
    font-size: 13px;
}

.speed-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 10px;
    background: rgba(220, 53, 69, 0.08);
    color: #dc3545;
    font-weight: 700;
    font-size: 13px;
}

.details-cell {
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.loading-box,
.empty-box {
    padding: 20px;
    text-align: center;
    color: #6c757d;
    font-weight: 600;
}

/* MAPPING MODAL - Updated styles */
.modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.35);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
}

.modal-dialog-custom {
    width: 650px;
    max-width: calc(100vw - 24px);
    max-height: 80vh;
    margin: 16px;
}

.mapping-modal-card {
    background: #fff;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(15, 23, 42, 0.2);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    max-height: 80vh;
}

.modal-header-custom {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid #eef1f4;
    background: #fff;
}

.modal-title-custom {
    font-size: 17px;
    font-weight: 700;
    color: #111;
    margin: 0;
}

.btn-close-custom {
    width: 32px;
    height: 32px;
    border: 0;
    background: transparent;
    font-size: 22px;
    color: #6c757d;
    cursor: pointer;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: 0.15s ease;
}

.btn-close-custom:hover {
    background: #f0f2f5;
    color: #111;
}

.modal-body-custom {
    padding: 20px;
    overflow-y: auto;
    flex: 1;
    background: #f8f9fa;
}

.mapping-info {
    background: #f0f4ff;
    border-radius: 12px;
    padding: 12px 14px;
    font-size: 13px;
    color: #0d6efd;
    margin-bottom: 16px;
    line-height: 1.4;
}

.mapping-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.mapping-item {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #fff;
    padding: 10px 12px;
    border-radius: 12px;
    border: 1px solid #eef1f4;
}

.mapping-source {
    min-width: 180px;
    font-weight: 600;
    font-size: 14px;
    color: #111;
}

.mapping-select {
    flex: 1;
    border-radius: 10px;
    border: 1px solid #dfe3e8;
    padding: 8px 12px;
    font-size: 14px;
    background: #fff;
    font-weight: 500;
}

.mapping-select.mapped {
    border-color: #198754;
    background: rgba(25, 135, 84, 0.04);
}

.mapping-select.unmapped {
    border-color: #dc3545;
    background: rgba(220, 53, 69, 0.04);
}

.modal-footer-custom {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 16px 20px;
    border-top: 1px solid #eef1f4;
    background: #fff;
}

.btn-cancel,
.btn-save {
    border: 0;
    border-radius: 14px;
    padding: 12px 20px;
    font-weight: 700;
    font-size: 14px;
    transition: 0.2s ease;
    cursor: pointer;
}

.btn-cancel {
    background: #eef1f4;
    color: #111;
}

.btn-cancel:hover {
    background: #dfe3e8;
}

.btn-save {
    background: #0d6efd;
    color: #fff;
}

.btn-save:hover:not(:disabled) {
    background: #0b5ed7;
}

.btn-save:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.fade-enter-active,
.fade-leave-active {
    transition: 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}

.fade-enter-from .modal-dialog-custom,
.fade-leave-to .modal-dialog-custom {
    transform: scale(0.95);
}

@media (max-width: 991.98px) {
    .custom-card {
        padding: 18px;
        border-radius: 20px;
    }

    .page-title {
        font-size: 22px;
    }

    .btn-create,
    .btn-convert,
    .btn-outline {
        width: 100%;
        justify-content: center;
    }

    .import-item {
        flex-direction: column;
        align-items: flex-start;
        gap: 6px;
    }

    .custom-table {
        font-size: 12px;
    }

    .custom-table th,
    .custom-table td {
        padding: 10px 12px;
    }

    .mapping-source {
        min-width: 120px;
        font-size: 13px;
    }
}

.badge-count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 24px;
    height: 24px;
    border-radius: 12px;
    background: rgba(13, 110, 253, 0.1);
    color: #0d6efd;
    font-size: 13px;
    font-weight: 700;
    padding: 0 8px;
    margin-left: 8px;
}

.mapping-summary {
    text-align: right;
    font-size: 13px;
    color: #6c757d;
    font-weight: 600;
}
</style>
