<script setup>
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from "vue";
import axios from "axios";
import accidentIcon from "@/assets/accident.png";
import cameraIcon from "@/assets/camera.png";
import clearIcon from "@/assets/clear.png";
import policeIcon from "@/assets/police.png";
import likeIcon from "@/assets/like.png";
import dislikeIcon from "@/assets/dislike.png";
import confidenceHighIcon from "@/assets/confidence high.png";
import confidenceMediumIcon from "@/assets/confidence medium .png";
import confidenceLowIcon from "@/assets/confidence low.png";
import defaultEventIcon from "@/assets/default.png";

const mapContainer = ref(null);
const mapState = ref({ map: null, ymaps: null, zoomControl: null, addCollection: null, zoneCollection: null });

let clusterer = null;
let updateTimer = null;
let resizeHandler = null;
let addPointPlacemark = null;
let addMarkerUpdateTimer = null;
let clusterUpdateTimer = null;
let clusterLayoutClass = null;
let pocketZoneStates = [];
let isDisposed = false;
let resizeObserver = null;

const DEFAULT_CENTER = [52.329514, 104.298266];
const categoryImageByCode = ref({});
const categoryImageById = ref({});
const eventsList = ref([]);
const pocketPointsList = ref([]);
const pocketCategories = ref([]);
const categories = ref([]);
const selectedEvent = ref(null);
const selectedPocketPoint = ref(null);
const editCategoryId = ref(null);
const isSaving = ref(false);
const isDeleting = ref(false);
const modalError = ref("");
const showEventModal = ref(false);
const showPocketModal = ref(false);
const isEditMode = ref(false);
const showFilterPanel = ref(false);
const appliedCategoryFilters = ref([]);
const draftCategoryFilters = ref([]);
const filtersInitialized = ref(false);
const showAddEventPanel = ref(false);
const addEventStep = ref(1);
const selectedAddCategoryId = ref(null);
const selectedAddDetail = ref("");
const addComment = ref("");
const addEventBusy = ref(false);
const addEventError = ref("");
const selectedAddPoint = ref(null);
const TARGET_REGION_NAME = "Иркутская область";
const BASE_CLUSTER_GRID_SIZE = 420;
const ZONE_MIN_ZOOM = 15;
const ZONE_CAMERA_TYPE_CODES = new Set(["1"]);
const addHintText = computed(() => {
    if (!showAddEventPanel.value) return "";
    return selectedAddPoint.value
        ? "Место выбрано. Укажите категорию и нажмите «Добавить»"
        : "Выберите место для дорожного события";
});

function loadYandexMaps() {
    return new Promise((resolve, reject) => {
        if (window.ymaps) {
            window.ymaps.ready(() => resolve(window.ymaps));
            return;
        }

        const apiKey = import.meta.env.VITE_YANDEX_MAPS_API_KEY;
        if (!apiKey) {
            reject(new Error("VITE_YANDEX_MAPS_API_KEY is not set"));
            return;
        }

        const script = document.createElement("script");
        script.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`;
        script.async = true;
        script.onload = () => window.ymaps.ready(() => resolve(window.ymaps));
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

function eventPreset(categoryCode) {
    const code = (categoryCode || "").toLowerCase();
    if (code === "dps") return "islands#redIcon";
    if (code === "camera") return "islands#greenIcon";
    if (code === "clear") return "islands#grayIcon";
    if (code === "crash") return "islands#orangeIcon";
    return "islands#blueIcon";
}

function normalizeCategoryCode(value) {
    return String(value || "").trim().toLowerCase();
}

function categoryKeyForEvent(event) {
    if (event?.category_id) return `road:${event.category_id}`;
    const code = normalizeCategoryCode(event?.category_code);
    return `road-code:${code || "other"}`;
}

function categoryKeyForPocketPoint(point) {
    if (point?.category) return `pocket:${point.category}`;
    const code = normalizeCategoryCode(point?.type_code || point?.category_name || point?.category);
    return `pocket-code:${code || "other"}`;
}

function categoryCodeFromName(name) {
    const raw = normalizeCategoryCode(name);
    if (raw.includes("камер")) return "camera";
    if (raw.includes("дтп") || raw.includes("авар")) return "crash";
    if (raw.includes("дпс")) return "dps";
    if (raw.includes("чист")) return "clear";
    if (raw.includes("работ")) return "road_work";
    if (raw.includes("перекры")) return "block";
    if (raw.includes("помощ")) return "help";
    if (raw.includes("проч")) return "other";
    return raw || "other";
}

function eventIcon(event) {
    const code = normalizeCategoryCode(event?.category_code);
    const byId = categoryImageById.value[event?.category_id];
    if (byId) return byId;
    const dynamicIcon = categoryImageByCode.value[code];
    if (dynamicIcon) return dynamicIcon;
    if (code === "dps") return policeIcon;
    if (code === "camera") return cameraIcon;
    if (code === "clear") return clearIcon;
    if (code === "crash") return accidentIcon;
    return null;
}

function categoryIcon(category) {
    if (category?.image) return resolveMediaUrl(category.image);
    return eventIcon({ category_code: categoryCodeFromName(category?.name), category_id: category?.id }) || policeIcon;
}

function getPlacemarkCategoryKey(geoObject) {
    if (geoObject?.properties?.get) {
        return geoObject.properties.get("category_key") || "other";
    }
    return geoObject?.properties?.category_key || "other";
}

function getPlacemarkIcon(geoObject) {
    if (geoObject?.properties?.get) {
        return geoObject.properties.get("category_icon") || null;
    }
    return geoObject?.properties?.category_icon || null;
}

function resolveMediaUrl(path) {
    if (!path) return "";
    if (path.startsWith("http://") || path.startsWith("https://")) return path;
    return path.startsWith("/") ? path : `/${path}`;
}

function createClusterLayout(ymaps) {
    return ymaps.templateLayoutFactory.createClass("<div></div>", {
        build() {
            this.constructor.superclass.build.call(this);

            const geoObjects = this.getData()?.properties?.get("geoObjects") || [];
            const groupsMap = new Map();

            for (const geoObject of geoObjects) {
                const key = getPlacemarkCategoryKey(geoObject);
                const icon = getPlacemarkIcon(geoObject) || policeIcon;
                const group = groupsMap.get(key) || { count: 0, icon };
                group.count += 1;
                groupsMap.set(key, group);
            }

            const allGroups = Array.from(groupsMap.values()).sort((a, b) => b.count - a.count);
            const mapZoom = Number(this.getData()?.geoObject?.getMap?.()?.getZoom?.());
            const isFarZoom = Number.isFinite(mapZoom) && mapZoom <= 11;
            const isMidZoom = Number.isFinite(mapZoom) && mapZoom > 11 && mapZoom <= 13;

            const maxItemsPerRow = isFarZoom ? 3 : isMidZoom ? 4 : 5;
            const maxVisibleGroups = isFarZoom ? 6 : isMidZoom ? 8 : 12;
            const groups = allGroups.slice(0, maxVisibleGroups);
            const hiddenGroupsCount = Math.max(0, allGroups.length - groups.length);

            const itemWidth = isFarZoom ? 42 : 46;
            const rowHeight = isFarZoom ? 22 : 24;
            const rows = [];
            for (let i = 0; i < groups.length; i += maxItemsPerRow) {
                rows.push(groups.slice(i, i + maxItemsPerRow));
            }
            if (hiddenGroupsCount > 0) {
                const tailItem = { count: `+${hiddenGroupsCount}`, icon: null };
                if (!rows.length || rows[rows.length - 1].length >= maxItemsPerRow) rows.push([tailItem]);
                else rows[rows.length - 1].push(tailItem);
            }

            const cols = Math.min(maxItemsPerRow, groups.length || 1);
            this._width = Math.max(68, cols * itemWidth + 12);
            this._height = Math.max(30, rows.length * rowHeight + 8);

            const rowsHtml = rows
                .map(
                    (row) => `
                    <div style="display:flex;align-items:center;justify-content:center;gap:8px;min-height:${rowHeight}px;">
                        ${row
                            .map(
                                (group) => `
                                <div style="display:flex;align-items:center;gap:5px;min-width:${itemWidth - 6}px;justify-content:center;">
                                    ${group.icon ? `<img src="${group.icon}" style="width:14px;height:14px;display:block;" />` : ""}
                                    <span style="font-size:13px;line-height:1;font-weight:700;color:#111;">${group.count}</span>
                                </div>
                            `
                            )
                            .join("")}
                    </div>
                `
                )
                .join("");

            const html = `
                <div style="
                    width:${this._width}px;
                    height:${this._height}px;
                    border-radius:15px;
                    background:#fff;
                    box-shadow:0 4px 16px rgba(0,0,0,0.22);
                    display:flex;
                    flex-direction:column;
                    align-items:center;
                    justify-content:center;
                    padding:4px 6px;
                    transform:translate(-50%,-50%);
                ">
                    ${rowsHtml}
                </div>
            `;

            this.getParentElement().innerHTML = html;
        },

        clear() {
            this.getParentElement().innerHTML = "";
            this.constructor.superclass.clear.call(this);
        },

        getShape() {
            const width = this._width || 120;
            const height = this._height || 64;
            return new ymaps.shape.Rectangle(
                new ymaps.geometry.pixel.Rectangle([
                    [-width / 2, -height / 2],
                    [width / 2, height / 2],
                ])
            );
        },
    });
}

function calcClusterGridSizeByZoom(zoom) {
    const z = Number(zoom);
    if (!Number.isFinite(z)) return BASE_CLUSTER_GRID_SIZE;
    if (z <= 7) return 1400;
    if (z <= 8) return 1320;
    if (z <= 9) return 1240;
    if (z <= 10) return 1120;
    if (z <= 11) return 980;
    if (z <= 12) return 820;
    if (z <= 13) return 680;
    if (z <= 14) return 560;
    return BASE_CLUSTER_GRID_SIZE;
}

function createClusterer(ymaps, map) {
    if (!clusterLayoutClass) {
        clusterLayoutClass = createClusterLayout(ymaps);
    }
    const instance = new ymaps.Clusterer({
        clusterIconLayout: clusterLayoutClass,
        groupByCoordinates: false,
        gridSize: BASE_CLUSTER_GRID_SIZE,
        minClusterSize: 2,
        clusterDisableClickZoom: false,
        clusterOpenBalloonOnClick: false,
    });
    map.geoObjects.add(instance);
    instance.options.set("gridSize", calcClusterGridSizeByZoom(map.getZoom()));
    return instance;
}

function unmountClusterer() {
    const map = mapState.value.map;
    if (map && clusterer) {
        try {
            map.geoObjects.remove(clusterer);
        } catch (e) {
            console.error("Не удалось снять Clusterer с карты:", e);
        }
    }
    clusterer = null;
}

function normalizeEvents(payload) {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.results)) return payload.results;
    return [];
}

function buildPlacemarks(events, ymaps) {
    const placemarks = [];

    for (const event of events) {
        const coords = event?.location?.coordinates;
        if (!Array.isArray(coords) || coords.length !== 2) continue;

        const lon = Number(coords[0]);
        const lat = Number(coords[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
        if (Math.abs(lat) > 90 || Math.abs(lon) > 180) continue;

        const code = normalizeCategoryCode(event.category_code);
        const icon = eventIcon(event);
        const categoryKey = categoryKeyForEvent(event);
        const placemark = new ymaps.Placemark(
            [lat, lon],
            {
                category_code: code,
                category_key: categoryKey,
                category_icon: icon || policeIcon,
                event_id: event.id,
            },
            icon
                ? {
                    hasBalloon: false,
                    iconLayout: "default#image",
                    iconImageHref: icon,
                    iconImageSize: [28, 28],
                    // Привязка координаты к "носику" иконки (нижняя центральная точка)
                    iconImageOffset: [-14, -28],
                }
                : {
                    hasBalloon: false,
                    preset: eventPreset(event.category_code),
                }
        );
        placemark.events.add("click", () => openEventModal(event));

        placemarks.push(placemark);
    }

    return placemarks;
}

function buildPocketGisPlacemarks(points, ymaps) {
    const placemarks = [];
    const states = [];
    for (const point of points) {
        const coords = point?.location?.coordinates;
        if (!Array.isArray(coords) || coords.length !== 2) continue;

        const lon = Number(coords[0]);
        const lat = Number(coords[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
        if (Math.abs(lat) > 90 || Math.abs(lon) > 180) continue;

        const icon = point?.category_icon ? resolveMediaUrl(point.category_icon) : defaultEventIcon;
        const categoryKey = categoryKeyForPocketPoint(point);
        const placemark = new ymaps.Placemark(
            [lat, lon],
            {
                category_code: "pocketgis",
                category_key: categoryKey,
                category_icon: icon,
                point_id: point.id,
            },
            {
                hasBalloon: false,
                iconLayout: "default#image",
                iconImageHref: icon,
                iconImageSize: [24, 24],
                // Привязка координаты к нижней точке иконки
                iconImageOffset: [-12, -24],
            }
        );
        placemark.events.add("click", () => openPocketPointModal(point));

        placemarks.push(placemark);
        states.push({ placemark, point, lat, lon });
    }
    return { placemarks, states };
}

function normalizeAngle360(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return 0;
    return ((n % 360) + 360) % 360;
}

function destinationByDistanceAndBearing(lat, lon, bearingDeg, distanceM) {
    const R = 6378137;
    const brng = (bearingDeg * Math.PI) / 180;
    const d = Number(distanceM) / R;
    const lat1 = (lat * Math.PI) / 180;
    const lon1 = (lon * Math.PI) / 180;

    const lat2 = Math.asin(
        Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(brng)
    );
    const lon2 =
        lon1 +
        Math.atan2(
            Math.sin(brng) * Math.sin(d) * Math.cos(lat1),
            Math.cos(d) - Math.sin(lat1) * Math.sin(lat2)
        );

    return [(lat2 * 180) / Math.PI, (lon2 * 180) / Math.PI];
}

function buildSectorPoints(lat, lon, centerAzimuth, angleDeg, distanceM) {
    const distance = Math.max(10, Math.min(Number(distanceM), 10000));
    const angle = Math.max(5, Math.min(360, Number(angleDeg) || 60));
    const steps = Math.max(12, Math.min(48, Math.round(angle / 4)));
    const start = normalizeAngle360(centerAzimuth - angle / 2);
    const end = normalizeAngle360(centerAzimuth + angle / 2);
    const diff = start <= end ? end - start : 360 - (start - end);

    const points = [[lat, lon]];
    for (let i = 0; i <= steps; i += 1) {
        const az = normalizeAngle360(start + (diff * i) / steps);
        points.push(destinationByDistanceAndBearing(lat, lon, az, distance));
    }
    points.push([lat, lon]);
    return points;
}

function shouldDrawZoneForPoint(point) {
    const typeCode = String(point?.type_code ?? point?.category ?? "").trim();
    return ZONE_CAMERA_TYPE_CODES.has(typeCode);
}

function renderPocketZones() {
    const { map, ymaps, zoneCollection } = mapState.value;
    if (!map || !ymaps || !zoneCollection || !clusterer) return;

    zoneCollection.removeAll();
    if (showAddEventPanel.value) return;
    if (map.getZoom() < ZONE_MIN_ZOOM) return;

    for (const state of pocketZoneStates) {
        const { placemark, point, lat, lon } = state;
        if (!shouldDrawZoneForPoint(point)) continue;

        const objectState = clusterer.getObjectState?.(placemark);
        if (!objectState || !objectState.isShown || objectState.isClustered) continue;

        const distance = Number(point?.distance);
        if (!Number.isFinite(distance) || distance <= 0) continue;

        const direction = normalizeAngle360(point?.direction);
        const dirType = Number(point?.dir_type) === 2 ? 2 : 1;
        const angle = Number(point?.angle);

        const primaryPoints = buildSectorPoints(lat, lon, direction, angle, distance);
        const primaryZone = new ymaps.GeoObject(
            {
                geometry: {
                    type: "Polygon",
                    coordinates: [primaryPoints],
                },
            },
            {
                fillColor: "rgba(33, 150, 243, 0.22)",
                strokeColor: "rgba(33, 150, 243, 0.55)",
                strokeWidth: 1.5,
                interactivityModel: "default#transparent",
            }
        );
        zoneCollection.add(primaryZone);

        if (dirType === 2) {
            const oppositePoints = buildSectorPoints(lat, lon, direction + 180, angle, distance);
            const oppositeZone = new ymaps.GeoObject(
                {
                    geometry: {
                        type: "Polygon",
                        coordinates: [oppositePoints],
                    },
                },
                {
                    fillColor: "rgba(33, 150, 243, 0.22)",
                    strokeColor: "rgba(33, 150, 243, 0.55)",
                    strokeWidth: 1.5,
                    interactivityModel: "default#transparent",
                }
            );
            zoneCollection.add(oppositeZone);
        }
    }
}

function renderEvents() {
    const { map, ymaps, zoneCollection } = mapState.value;
    if (!map || !ymaps || !clusterer) return;

    if (showAddEventPanel.value) {
        clusterer.removeAll();
        if (zoneCollection) zoneCollection.removeAll();
        return;
    }

    const roadPlacemarks = buildPlacemarks(filteredEvents.value, ymaps);
    const { placemarks: pocketPlacemarks, states } = buildPocketGisPlacemarks(filteredPocketPoints.value, ymaps);
    pocketZoneStates = states;
    const placemarks = [...roadPlacemarks, ...pocketPlacemarks];
    try {
        clusterer.removeAll();
        clusterer.add(placemarks);
    } catch (e) {
        console.error("Ошибка отрисовки кластера:", e);
        return;
    }
    renderPocketZones();
}

const filterOptions = computed(() => {
    const optionsMap = new Map();

    for (const cat of categories.value) {
        const key = cat?.id ? `road:${cat.id}` : `road-code:${normalizeCategoryCode(cat?.name) || "other"}`;
        if (!key) continue;

        const code = normalizeCategoryCode(cat?.name);
        const icon = cat?.image ? resolveMediaUrl(cat.image) : categoryImageByCode.value[code] || null;
        optionsMap.set(key, {
            key,
            label: cat?.name || code || "Прочее",
            icon: icon || policeIcon,
        });
    }

    for (const event of eventsList.value) {
        const key = categoryKeyForEvent(event);
        if (optionsMap.has(key)) continue;
        optionsMap.set(key, {
            key,
            label: event?.category_label || event?.category_code || "Прочее",
            icon: eventIcon(event) || policeIcon,
        });
    }

    for (const cat of pocketCategories.value) {
        const key = cat?.id ? `pocket:${cat.id}` : `pocket-code:${normalizeCategoryCode(cat?.type_code || cat?.name)}`;
        if (!key || optionsMap.has(key)) continue;
        optionsMap.set(key, {
            key,
            label: cat?.name || cat?.type_code || "PocketGIS",
            icon: cat?.icon ? resolveMediaUrl(cat.icon) : defaultEventIcon,
        });
    }

    for (const point of pocketPointsList.value) {
        const key = categoryKeyForPocketPoint(point);
        if (optionsMap.has(key)) continue;
        optionsMap.set(key, {
            key,
            label: point?.category_name || point?.type_code || "PocketGIS",
            icon: point?.category_icon ? resolveMediaUrl(point.category_icon) : defaultEventIcon,
        });
    }

    return Array.from(optionsMap.values()).sort((a, b) => a.label.localeCompare(b.label, "ru"));
});

const filteredEvents = computed(() => {
    const active = new Set(appliedCategoryFilters.value);
    if (!active.size) return [];
    return eventsList.value.filter((event) => active.has(categoryKeyForEvent(event)));
});

const filteredPocketPoints = computed(() => {
    const active = new Set(appliedCategoryFilters.value);
    if (!active.size) return [];
    return pocketPointsList.value.filter((point) => active.has(categoryKeyForPocketPoint(point)));
});

function ensureFilterState() {
    const keys = filterOptions.value.map((o) => o.key);
    if (!keys.length) return;

    // Инициализируем фильтры только один раз (первый запуск страницы).
    // Дальше не пере-включаем категории, чтобы пользовательский выбор не сбрасывался.
    if (!filtersInitialized.value) {
        appliedCategoryFilters.value = [...keys];
        draftCategoryFilters.value = [...keys];
        filtersInitialized.value = true;
        return;
    }

    const keysSet = new Set(keys);
    const appliedSet = new Set(appliedCategoryFilters.value.filter((k) => keysSet.has(k)));
    const draftSet = new Set(draftCategoryFilters.value.filter((k) => keysSet.has(k)));

    // Если драфт пуст (например, открывали панель впервые после загрузки новых данных),
    // подтянем его из текущего примененного состояния.
    if (!draftSet.size && appliedSet.size) {
        for (const key of appliedSet) draftSet.add(key);
    }

    appliedCategoryFilters.value = keys.filter((k) => appliedSet.has(k));
    draftCategoryFilters.value = keys.filter((k) => draftSet.has(k));
}

function toggleFilterPanel() {
    if (showFilterPanel.value) {
        showFilterPanel.value = false;
        return;
    }
    draftCategoryFilters.value = [...appliedCategoryFilters.value];
    showFilterPanel.value = true;
}

function applyCategoryFilters() {
    appliedCategoryFilters.value = [...draftCategoryFilters.value];
    showFilterPanel.value = false;
    renderEvents();
}

function resetCategoryFilters() {
    const keys = filterOptions.value.map((o) => o.key);
    draftCategoryFilters.value = [...keys];
    appliedCategoryFilters.value = [...keys];
    showFilterPanel.value = false;
    renderEvents();
}

function toggleDraftCategory(key) {
    const set = new Set(draftCategoryFilters.value);
    if (set.has(key)) {
        set.delete(key);
    } else {
        set.add(key);
    }
    draftCategoryFilters.value = filterOptions.value.map((o) => o.key).filter((k) => set.has(k));
}

async function loadEvents() {
    try {
        const { data: payload } = await axios.get("/api/events/road-events/");
        if (isDisposed) return;
        const events = normalizeEvents(payload);
        eventsList.value = events;
        ensureFilterState();
        renderEvents();
        if (selectedEvent.value?.id) {
            const fresh = events.find((e) => e.id === selectedEvent.value.id);
            if (fresh) {
                selectedEvent.value = fresh;
            } else {
                closeEventModal();
            }
        }
    } catch (e) {
        console.error("Ошибка загрузки событий:", e);
    }
}

async function loadPocketGisPoints() {
    try {
        const { data: regionsPayload } = await axios.get("/api/regions/");
        if (isDisposed) return;
        const regions = Array.isArray(regionsPayload) ? regionsPayload : [];
        const region = regions.find(
            (r) => String(r?.name || "").trim().toLowerCase() === TARGET_REGION_NAME.toLowerCase()
        );
        if (!region?.id) {
            pocketPointsList.value = [];
            if (!isDisposed) renderEvents();
            return;
        }

        let offset = 0;
        const limit = 5000;
        let total = 0;
        const loaded = [];

        do {
            const { data } = await axios.get("/api/events/pocketgis/points/", {
                params: {
                    region: region.id,
                    limit,
                    offset,
                },
            });
            const rows = Array.isArray(data?.results) ? data.results : [];
            total = Number(data?.count || 0);
            loaded.push(...rows);
            offset += rows.length;
            if (!rows.length) break;
        } while (offset < total);

        if (isDisposed) return;
        pocketPointsList.value = loaded;
        ensureFilterState();
        renderEvents();
    } catch (e) {
        console.error("Ошибка загрузки точек PocketGis:", e);
    }
}

async function loadPocketGisCategories() {
    try {
        const { data } = await axios.get("/api/events/pocketgis/categories/");
        if (isDisposed) return;
        pocketCategories.value = Array.isArray(data) ? data : [];
        ensureFilterState();
    } catch (e) {
        console.error("Ошибка загрузки категорий PocketGis:", e);
    }
}

async function loadCategories() {
    try {
        const { data } = await axios.get("/api/alert_categories/");
        if (isDisposed) return;
        categories.value = Array.isArray(data) ? data : [];
        categoryImageByCode.value = categories.value.reduce((acc, cat) => {
            const code = normalizeCategoryCode(cat?.name);
            if (code && cat?.image) {
                acc[code] = resolveMediaUrl(cat.image);
            }
            return acc;
        }, {});
        categoryImageById.value = categories.value.reduce((acc, cat) => {
            if (cat?.id && cat?.image) {
                acc[cat.id] = resolveMediaUrl(cat.image);
            }
            return acc;
        }, {});
        ensureFilterState();
    } catch (e) {
        console.error("Ошибка загрузки категорий:", e);
    }
}

function openEventModal(event) {
    closePocketPointModal();
    selectedEvent.value = event;
    editCategoryId.value = event.category_id;
    modalError.value = "";
    showEventModal.value = true;
}

function closeEventModal() {
    showEventModal.value = false;
    selectedEvent.value = null;
    editCategoryId.value = null;
    modalError.value = "";
    isEditMode.value = false;
}

function openPocketPointModal(point) {
    closeEventModal();
    selectedPocketPoint.value = point;
    showPocketModal.value = true;
}

function closePocketPointModal() {
    showPocketModal.value = false;
    selectedPocketPoint.value = null;
}

const pocketPointTitle = computed(() => {
    const p = selectedPocketPoint.value;
    return p?.category_name || p?.type_code || "Точка PocketGis";
});

const pocketPointSubtitle = computed(() => {
    const p = selectedPocketPoint.value;
    if (!p) return "";
    const parts = [];
    if (p.speed_limit) parts.push(`Ограничение: ${p.speed_limit}`);
    if (p.distance) parts.push(`Дистанция: ${p.distance}`);
    if (p.direction) parts.push(`Направление: ${p.direction}`);
    return parts.join(" • ");
});

const addCategoryItems = computed(() => {
    return (categories.value || []).map((cat) => ({
        id: cat.id,
        name: cat.name,
        code: categoryCodeFromName(cat.name),
        icon: categoryIcon(cat),
    }));
});

const selectedAddCategory = computed(() => {
    return addCategoryItems.value.find((item) => item.id === Number(selectedAddCategoryId.value)) || null;
});

const addDetailOptionsByCode = {
    camera: ["На скорость", "Контроль перекрестка", "На полосу, разметку", "Мобильная засада"],
    crash: ["Левый ряд", "Средний ряд", "Правый ряд", "Серьезное ДТП"],
    dps: ["Пост", "Рейд", "Экипаж", "Проверка"],
    road_work: ["Левый ряд", "Средний ряд", "Правый ряд", "Сужение"],
    help: ["Эвакуатор", "Медпомощь", "Нужна помощь", "Другое"],
    block: ["Полное", "Частичное", "Объезд", "Проверить"],
    other: ["Опасность", "Препятствие", "Пробка", "Иное"],
    clear: ["Пост снят", "Камеры нет", "Проезд свободен", "Проверить"],
};

const addDetailOptions = computed(() => {
    const code = selectedAddCategory.value?.code || "other";
    return addDetailOptionsByCode[code] || addDetailOptionsByCode.other;
});

function getAddMarkerIconHref() {
    return selectedAddCategory.value?.icon || defaultEventIcon;
}

function applyAddMarkerIcon(placemark) {
    if (!placemark) return;
    const href = getAddMarkerIconHref();
    placemark.options.set("iconLayout", "default#image");
    placemark.options.set("iconImageHref", href);
    placemark.options.set("iconImageSize", [36, 36]);
    placemark.options.set("iconImageOffset", [-18, -36]);
    placemark.options.set("hasBalloon", false);
}

function rebuildAddPointMarker() {
    const map = mapState.value.map;
    const ymaps = mapState.value.ymaps;
    const addCollection = mapState.value.addCollection;
    const point = selectedAddPoint.value;
    if (!map || !ymaps || !addCollection || !Array.isArray(point) || point.length !== 2) return;

    const lat = Number(point[0]);
    const lon = Number(point[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

    try {
        addCollection.removeAll();
        addPointPlacemark = new ymaps.Placemark([lat, lon], {}, {});
        applyAddMarkerIcon(addPointPlacemark);
        addCollection.add(addPointPlacemark);
    } catch (e) {
        console.error("Не удалось отрисовать маркер добавления:", e);
    }
}

function openAddEventPanel() {
    if (showAddEventPanel.value) {
        closeAddEventPanel();
        return;
    }
    showAddEventPanel.value = true;
    addEventStep.value = 1;
    selectedAddCategoryId.value = null;
    selectedAddDetail.value = "";
    addComment.value = "";
    addEventError.value = "";
    selectedAddPoint.value = null;
    showFilterPanel.value = false;
    closeEventModal();
    if (mapState.value.addCollection) {
        mapState.value.addCollection.removeAll();
    }
    addPointPlacemark = null;
    renderEvents();
}

function closeAddEventPanel() {
    showAddEventPanel.value = false;
    addEventStep.value = 1;
    selectedAddCategoryId.value = null;
    selectedAddDetail.value = "";
    addComment.value = "";
    addEventError.value = "";
    selectedAddPoint.value = null;
    if (mapState.value.addCollection) {
        mapState.value.addCollection.removeAll();
    }
    addPointPlacemark = null;
    renderEvents();
}

function chooseAddCategory(id) {
    selectedAddCategoryId.value = id;
    selectedAddDetail.value = "";
    addEventError.value = "";
    addEventStep.value = 2;
    rebuildAddPointMarker();
}

function backAddEventStep() {
    addEventStep.value = 1;
    selectedAddDetail.value = "";
    addEventError.value = "";
}

function setAddPoint(coords) {
    if (!Array.isArray(coords) || coords.length !== 2) return;
    const lat = Number(coords[0]);
    const lon = Number(coords[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

    selectedAddPoint.value = [lat, lon];
    addEventError.value = "";
    // В Safari обновление geoObjects прямо внутри click-хендлера иногда ломает renderflow.
    // Делаем отложенное обновление маркера после завершения текущего события карты.
    if (addMarkerUpdateTimer) clearTimeout(addMarkerUpdateTimer);
    addMarkerUpdateTimer = setTimeout(() => {
        rebuildAddPointMarker();
        addMarkerUpdateTimer = null;
    }, 0);
}

async function createRoadEventFromMapCenter() {
    const map = mapState.value.map;
    const selected = selectedAddCategory.value;
    if (!map || !selected) return;
    if (!selectedAddPoint.value) {
        addEventError.value = "Сначала выберите место на карте";
        return;
    }
    const lat = Number(selectedAddPoint.value[0]);
    const lon = Number(selectedAddPoint.value[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        addEventError.value = "Не удалось получить координаты точки";
        return;
    }

    addEventBusy.value = true;
    addEventError.value = "";
    try {
        await axios.post("/api/events/road-events/", {
            location: {
                type: "Point",
                coordinates: [lon, lat],
            },
            category_id: selected.id,
            category_code: selected.code,
            category_label: selected.name,
            extra_params: selectedAddDetail.value ? { detail: selectedAddDetail.value } : {},
            comment: addComment.value || "",
        });
        await loadEvents();
        closeAddEventPanel();
    } catch (e) {
        addEventError.value = e?.response?.data?.detail || "Не удалось добавить дорожное событие";
    } finally {
        addEventBusy.value = false;
    }
}

const eventVoteStats = computed(() => {
    const event = selectedEvent.value;
    const votes = Array.isArray(event?.votes) ? event.votes : [];
    const confirmsFromVotes = votes.filter((v) => Number(v.vote) === 1).length;
    const denies = votes.filter((v) => Number(v.vote) === -1).length;
    const lastConfirm = votes
        .filter((v) => Number(v.vote) === 1 && v.created_at)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0];
    const lastDeny = votes
        .filter((v) => Number(v.vote) === -1 && v.created_at)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0];

    return {
        confirms: Number(event?.confirmations ?? confirmsFromVotes ?? 0),
        denies,
        lastConfirmText: lastConfirm ? `${timeAgo(lastConfirm.created_at)} назад` : "нет голосов",
        lastDenyText: lastDeny ? `${timeAgo(lastDeny.created_at)} назад` : "нет голосов",
    };
});

const eventMetaText = computed(() => {
    const event = selectedEvent.value;
    if (!event) return "";
    const created = event.created_at ? `${timeAgo(event.created_at)} назад` : "недавно";
    const author = event.extra_params?.author_name || "автор не указан";
    const source = event.source === "telegram" ? "Telegram" : "пользователь";
    return `${created}, ${author}, ${source}`;
});

const eventDescription = computed(() => {
    const event = selectedEvent.value;
    if (!event) return "";
    return event.comment || event.extra_params?.place_name || "Комментарий отсутствует";
});

const confidencePercent = computed(() => {
    const value = Number(selectedEvent.value?.confidence ?? 0);
    const normalized = Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
    return Math.round(normalized * 100);
});

const confidenceIcon = computed(() => {
    const score = confidencePercent.value;
    if (score >= 75) return confidenceHighIcon;
    if (score >= 45) return confidenceMediumIcon;
    return confidenceLowIcon;
});

const confidenceClass = computed(() => {
    const score = confidencePercent.value;
    if (score >= 75) return "confidence-high";
    if (score >= 45) return "confidence-medium";
    return "confidence-low";
});

async function saveEventCategory() {
    if (!selectedEvent.value) return;
    const category = categories.value.find((c) => c.id === Number(editCategoryId.value));
    if (!category) {
        modalError.value = "Выберите категорию";
        return;
    }

    isSaving.value = true;
    modalError.value = "";
    try {
        const event = selectedEvent.value;
        await axios.put(`/api/events/road-events/${event.id}/`, {
            source_message: event.source_message,
            location: event.location,
            category_id: category.id,
            category_code: category.name,
            category_label: category.name,
            extra_params: event.extra_params || {},
            comment: event.comment || "",
            user_id: event.user_id,
            status: event.status,
            source: event.source,
            confidence: event.confidence,
            confirmations: event.confirmations,
            valid_until: event.valid_until,
        });
        await loadEvents();
        isEditMode.value = false;
    } catch (e) {
        modalError.value = e?.response?.data?.detail || "Не удалось изменить категорию";
    } finally {
        isSaving.value = false;
    }
}

async function deleteEvent() {
    if (!selectedEvent.value) return;
    if (!window.confirm("Удалить это дорожное событие?")) return;

    isDeleting.value = true;
    modalError.value = "";
    try {
        await axios.delete(`/api/events/road-events/${selectedEvent.value.id}/`);
        closeEventModal();
        await loadEvents();
    } catch (e) {
        modalError.value = e?.response?.data?.detail || "Не удалось удалить событие";
    } finally {
        isDeleting.value = false;
    }
}

function timeAgo(inputDate) {
    const date = new Date(inputDate);
    const diffSeconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
    if (diffSeconds < 60) return `${diffSeconds} сек`;
    const minutes = Math.floor(diffSeconds / 60);
    if (minutes < 60) return `${minutes} мин`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} ч`;
    const days = Math.floor(hours / 24);
    return `${days} д`;
}

function positionZoomControl() {
    const { map, zoomControl } = mapState.value;
    if (!map || !zoomControl) return;
    const size = map.container?.getSize?.();
    const height = Array.isArray(size) ? Number(size[1]) : NaN;
    if (!Number.isFinite(height) || height <= 0) return;

    // Центрируем зум-контрол по правому краю карты.
    const top = Math.max(12, Math.round(height / 2) - 56);
    zoomControl.options.set("position", { right: 12, top });
}

function refreshMapViewport() {
    const map = mapState.value.map;
    if (!map) return;
    try {
        map.container.fitToViewport();
        positionZoomControl();
        renderPocketZones();
    } catch (e) {
        console.error("Ошибка обновления viewport карты:", e);
    }
}

async function initMap() {
    const ymaps = await loadYandexMaps();
    clusterLayoutClass = createClusterLayout(ymaps);

    const map = new ymaps.Map(mapContainer.value, {
        center: DEFAULT_CENTER,
        zoom: 12,
        controls: [],
    });

    map.events.add("click", (e) => {
        if (!showAddEventPanel.value) return;
        const coords = e.get("coords");
        setAddPoint(coords);
    });
    map.events.add("boundschange", () => {
        if (clusterUpdateTimer) clearTimeout(clusterUpdateTimer);
        clusterUpdateTimer = setTimeout(() => {
            if (!clusterer || !mapState.value.map) {
                clusterUpdateTimer = null;
                return;
            }
            const nextGridSize = calcClusterGridSizeByZoom(mapState.value.map.getZoom());
            const currentGridSize = Number(clusterer.options.get("gridSize"));
            if (nextGridSize !== currentGridSize) {
                clusterer.options.set("gridSize", nextGridSize);
                renderEvents();
            } else {
                renderPocketZones();
            }
            clusterUpdateTimer = null;
        }, 90);
    });
    const addCollection = new ymaps.GeoObjectCollection();
    map.geoObjects.add(addCollection);
    const zoneCollection = new ymaps.GeoObjectCollection();
    map.geoObjects.add(zoneCollection);
    const zoomControl = new ymaps.control.ZoomControl({
        options: {
            size: "large",
            position: { right: 12, top: 220 },
        },
    });
    map.controls.add(zoomControl);

    const trafficControl = new ymaps.control.TrafficControl({
        state: {
            trafficShown: false,
            providerKey: "traffic#actual",
        },
        options: {
            position: { right: 12, top: 12 },
            size: "large",
        },
    });
    map.controls.add(trafficControl);

    mapState.value = { map, ymaps, zoomControl, addCollection, zoneCollection };
    clusterer = createClusterer(ymaps, map);
    positionZoomControl();

    await nextTick();
    requestAnimationFrame(() => {
        refreshMapViewport();
        requestAnimationFrame(() => refreshMapViewport());
    });

    await loadCategories();
    await loadPocketGisCategories();
    await Promise.allSettled([loadEvents(), loadPocketGisPoints()]);

    updateTimer = setInterval(() => {
        if (isDisposed) return;
        if (map.action?.isActive?.()) return;
        loadEvents();
    }, 30000);
}

onMounted(async () => {
    isDisposed = false;
    try {
        await initMap();
    } catch (e) {
        console.error("Ошибка инициализации карты:", e);
    }

    resizeHandler = () => refreshMapViewport();
    window.addEventListener("resize", resizeHandler);
    document.addEventListener("visibilitychange", resizeHandler);

    if (mapContainer.value && window.ResizeObserver) {
        resizeObserver = new ResizeObserver(() => refreshMapViewport());
        resizeObserver.observe(mapContainer.value);
    }
});

watch(selectedAddCategoryId, () => {
    rebuildAddPointMarker();
});

onUnmounted(() => {
    isDisposed = true;
    if (updateTimer) clearInterval(updateTimer);
    if (addMarkerUpdateTimer) {
        clearTimeout(addMarkerUpdateTimer);
        addMarkerUpdateTimer = null;
    }
    if (clusterUpdateTimer) {
        clearTimeout(clusterUpdateTimer);
        clusterUpdateTimer = null;
    }
    if (resizeHandler) {
        window.removeEventListener("resize", resizeHandler);
        document.removeEventListener("visibilitychange", resizeHandler);
        resizeHandler = null;
    }
    if (resizeObserver) {
        resizeObserver.disconnect();
        resizeObserver = null;
    }

    unmountClusterer();
    const { map } = mapState.value;
    if (map) map.destroy();
    clusterLayoutClass = null;
    pocketZoneStates = [];
    mapState.value = { map: null, ymaps: null, zoomControl: null, addCollection: null, zoneCollection: null };
});
</script>

<template>
    <div class="container-fluid p-3 map-page">
        <h4 class="mb-3">Карта дорожных событий</h4>
        <div class="map-wrap">
            <div ref="mapContainer" class="map-box"></div>

            <div class="map-controls-left">
                <button class="add-event-btn" type="button" title="Добавить дорожное событие" @click="openAddEventPanel">
                    <i class="bi bi-plus-lg"></i>
                </button>
            </div>

            <div class="map-controls-right">
                <button class="round-control" type="button" :disabled="showAddEventPanel" @click="toggleFilterPanel" title="Фильтры">
                    <i class="bi bi-sliders"></i>
                </button>
            </div>

            <transition name="filter-pop">
                <div v-if="showFilterPanel" class="filter-panel card shadow">
                    <div class="card-body p-3">
                        <div class="filter-list">
                            <div v-for="item in filterOptions" :key="item.key" class="filter-item" @click="toggleDraftCategory(item.key)">
                                <div class="filter-label-wrap">
                                    <img :src="item.icon" alt="" class="filter-icon" />
                                    <span class="filter-label">{{ item.label }}</span>
                                </div>
                                <button class="filter-check" :class="{ active: draftCategoryFilters.includes(item.key) }" type="button">
                                    <i v-if="draftCategoryFilters.includes(item.key)" class="bi bi-check-lg"></i>
                                </button>
                            </div>
                        </div>

                        <div class="filter-actions d-flex justify-content-end gap-2 mt-3">
                            <button type="button" class="btn btn-secondary btn-sm rounded-pill px-3 filter-action-btn" @click="resetCategoryFilters">
                                Сбросить
                            </button>
                            <button type="button" class="btn btn-primary btn-sm rounded-pill px-3 filter-action-btn" @click="applyCategoryFilters">
                                Применить
                            </button>
                        </div>
                    </div>
                </div>
            </transition>

            <transition name="add-panel-pop">
                <div v-if="showAddEventPanel" class="add-panel card shadow">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h3 class="add-event-title mb-0">
                                {{ addEventStep === 1 ? "Добавить дорожное событие" : `Добавить ${selectedAddCategory?.name || "событие"}` }}
                            </h3>
                            <button class="close-btn" @click="closeAddEventPanel">×</button>
                        </div>

                        <template v-if="addEventStep === 1">
                            <div class="category-grid">
                                <button
                                    v-for="item in addCategoryItems"
                                    :key="item.id"
                                    type="button"
                                    class="category-grid-item"
                                    @click="chooseAddCategory(item.id)"
                                >
                                    <img :src="item.icon" :alt="item.name" class="category-grid-icon" />
                                    <span class="category-grid-label">{{ item.name }}</span>
                                </button>
                            </div>

                            <div class="d-flex mt-3">
                                <button type="button" class="btn btn-secondary rounded-pill w-100 add-cancel-btn" @click="closeAddEventPanel">
                                    Отменить
                                </button>
                            </div>
                        </template>

                        <template v-else>
                            <div class="detail-options-grid">
                                <button
                                    v-for="option in addDetailOptions"
                                    :key="option"
                                    type="button"
                                    class="detail-option-btn"
                                    :class="{ active: selectedAddDetail === option }"
                                    @click="selectedAddDetail = option"
                                >
                                    <span class="detail-check">
                                        <i v-if="selectedAddDetail === option" class="bi bi-check-lg"></i>
                                    </span>
                                    <span class="detail-label">{{ option }}</span>
                                </button>
                            </div>

                            <input
                                v-model="addComment"
                                type="text"
                                class="form-control add-comment-input mt-3"
                                placeholder="Ваш комментарий"
                            />

                            <div v-if="addEventError" class="alert alert-danger py-2 mt-3 mb-0">{{ addEventError }}</div>

                            <div class="d-flex gap-2 mt-3">
                                <button type="button" class="btn btn-secondary rounded-pill flex-fill add-cancel-btn" @click="backAddEventStep">
                                    Назад
                                </button>
                                <button
                                    type="button"
                                    class="btn btn-primary rounded-pill flex-fill add-apply-btn"
                                    :disabled="addEventBusy"
                                    @click="createRoadEventFromMapCenter"
                                >
                                    {{ addEventBusy ? "Добавление..." : "Добавить" }}
                                </button>
                            </div>
                        </template>
                    </div>
                </div>
            </transition>

            <transition name="add-hint-fade">
                <div v-if="showAddEventPanel" class="add-mode-hint">
                    {{ addHintText }}
                </div>
            </transition>
        </div>

        <div v-if="showEventModal" class="modal-backdrop-custom">
            <div class="card shadow event-modal">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h2 class="event-title mb-0">{{ selectedEvent?.category_label || selectedEvent?.category_code || "Событие" }}</h2>
                        <button class="close-btn" @click="closeEventModal">×</button>
                    </div>

                    <div class="event-text mb-2">
                        {{ eventDescription }}
                    </div>
                    <div class="event-meta mb-4">{{ eventMetaText }}</div>

                    <div class="votes-row mb-4">
                        <div class="vote-group">
                            <div class="vote-pill vote-pill-up">
                                <span class="vote-number">{{ eventVoteStats.confirms }}</span>
                                <img :src="likeIcon" alt="like" />
                            </div>
                            <div class="vote-time">{{ eventVoteStats.lastConfirmText }}</div>
                        </div>
                        <div class="vote-group">
                            <div class="vote-pill vote-pill-down">
                                <span class="vote-number">{{ eventVoteStats.denies }}</span>
                                <img :src="dislikeIcon" alt="dislike" />
                            </div>
                            <div class="vote-time">{{ eventVoteStats.lastDenyText }}</div>
                        </div>
                    </div>

                    <div class="bottom-row mb-3">
                        <div class="confidence-wrap">
                            <img :src="confidenceIcon" alt="confidence" class="confidence-icon" />
                            <span class="confidence-value" :class="confidenceClass">{{ confidencePercent }}%</span>
                        </div>
                        <div class="actions-wrap">
                            <button class="action-btn action-btn-edit" :disabled="isSaving" @click="isEditMode = !isEditMode" title="Редактировать">
                                <i class="bi bi-pencil-fill"></i>
                            </button>
                            <button class="action-btn action-btn-delete" :disabled="isDeleting" @click="deleteEvent" title="Удалить">
                                <i class="bi bi-trash-fill"></i>
                            </button>
                        </div>
                    </div>

                    <div v-if="isEditMode" class="edit-panel mb-3">
                        <label class="form-label mb-1">Категория</label>
                        <div class="d-flex gap-2">
                            <select v-model="editCategoryId" class="form-select">
                                <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                                    {{ cat.name }}
                                </option>
                            </select>
                            <button class="btn btn-primary" :disabled="isSaving" @click="saveEventCategory">
                                {{ isSaving ? "..." : "OK" }}
                            </button>
                        </div>
                    </div>

                    <div v-if="modalError" class="alert alert-danger py-2 mb-3">{{ modalError }}</div>

                </div>
            </div>
        </div>

        <div v-if="showPocketModal" class="modal-backdrop-custom">
            <div class="card shadow event-modal">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h2 class="event-title mb-0">{{ pocketPointTitle }}</h2>
                        <button class="close-btn" @click="closePocketPointModal">×</button>
                    </div>

                    <div class="event-text mb-2">
                        {{ selectedPocketPoint?.details || "Детали не указаны" }}
                    </div>
                    <div class="event-meta mb-3">
                        {{ pocketPointSubtitle || "PocketGis" }}
                    </div>

                    <div class="pocket-grid">
                        <div class="pocket-row">
                            <span class="pocket-key">Регион</span>
                            <span class="pocket-val">{{ selectedPocketPoint?.region_name || "—" }}</span>
                        </div>
                        <div class="pocket-row">
                            <span class="pocket-key">Код типа</span>
                            <span class="pocket-val">{{ selectedPocketPoint?.type_code || "—" }}</span>
                        </div>
                        <div class="pocket-row">
                            <span class="pocket-key">Индекс</span>
                            <span class="pocket-val">{{ selectedPocketPoint?.external_idx || "—" }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.map-page {
    height: calc(100vh - 2rem);
    min-height: 640px;
    display: flex;
    flex-direction: column;
}

.map-box {
    width: 100%;
    height: 100%;
    min-height: 520px;
    border: 1px solid #d0d0d0;
    border-radius: 8px;
}

.map-wrap {
    position: relative;
    flex: 1;
    min-height: 520px;
}

.map-controls-right {
    position: absolute;
    right: 14px;
    top: 54px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    z-index: 20;
    align-items: flex-end;
}

.map-controls-left {
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 20;
}

.add-event-btn {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    border: none;
    background: #1976f3;
    color: #fff;
    font-size: 22px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.26);
}

.add-panel {
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    width: min(640px, calc(100% - 28px));
    max-width: 640px;
    border-radius: 22px;
    border: none;
    background: rgba(245, 245, 245, 0.98);
    z-index: 25;
}

.round-control {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: none;
    background: #f2f2f2;
    color: #444;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.filter-panel {
    position: absolute;
    right: 14px;
    top: 84px;
    width: 290px;
    border: none;
    border-radius: 18px;
    z-index: 20;
    background: rgba(248, 248, 248, 0.97);
}

.filter-pop-enter-active,
.filter-pop-leave-active {
    transition: transform 0.2s ease, opacity 0.2s ease;
    transform-origin: calc(100% - 24px) 14px;
}

.filter-pop-enter-from,
.filter-pop-leave-to {
    transform: scale(0.2);
    opacity: 0;
}

.filter-pop-enter-to,
.filter-pop-leave-from {
    transform: scale(1);
    opacity: 1;
}

.filter-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 340px;
    overflow: auto;
}

.filter-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
}

.filter-label-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
}

.filter-icon {
    width: 22px;
    height: 22px;
    object-fit: contain;
}

.filter-label {
    font-size: 16px;
    color: #222;
}

.filter-check {
    width: 27px;
    height: 27px;
    border-radius: 50%;
    border: 2px solid #2f89e0;
    background: #fff;
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
}

.filter-check.active {
    background: #2f89e0;
}

.filter-actions {
    align-items: center;
}

.filter-action-btn {
    min-height: 46px;
    line-height: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    font-weight: 500;
}

.add-event-title {
    font-size: 26px;
    font-weight: 700;
    color: #111;
    line-height: 1.05;
}

.category-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 20px 14px;
}

.category-grid-item {
    border: none;
    background: transparent;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    color: #1e1e1e;
}

.category-grid-icon {
    width: 54px;
    height: 54px;
    object-fit: contain;
}

.category-grid-label {
    font-size: 20px;
}

.add-cancel-btn,
.add-apply-btn {
    min-height: 46px;
    font-size: 20px;
}

.detail-options-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px 18px;
}

.detail-option-btn {
    border: none;
    background: transparent;
    text-align: left;
    display: flex;
    align-items: center;
    gap: 10px;
    color: #202020;
    padding: 4px 0;
}

.detail-check {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    border: 3px solid #2f89e0;
    color: #fff;
    background: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
}

.detail-option-btn.active .detail-check {
    background: #2f89e0;
}

.detail-label {
    font-size: 18px;
    line-height: 1.2;
}

.add-comment-input {
    border-radius: 18px;
    background: #f1f1f1;
    border: none;
    min-height: 44px;
    font-size: 20px;
}

.add-mode-hint {
    position: absolute;
    left: 50%;
    bottom: 14px;
    transform: translateX(-50%);
    background: rgba(245, 245, 245, 0.97);
    color: #171717;
    border-radius: 16px;
    padding: 12px 24px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
    z-index: 24;
    pointer-events: none;
    font-size: 28px;
}

.add-panel-pop-enter-active,
.add-panel-pop-leave-active {
    transition: transform 0.2s ease, opacity 0.2s ease;
    transform-origin: 24px 50%;
}

.add-panel-pop-enter-from,
.add-panel-pop-leave-to {
    transform: translateY(-50%) scale(0.25);
    opacity: 0;
}

.add-panel-pop-enter-to,
.add-panel-pop-leave-from {
    transform: translateY(-50%) scale(1);
    opacity: 1;
}

.add-hint-fade-enter-active,
.add-hint-fade-leave-active {
    transition: opacity 0.2s ease, transform 0.2s ease;
}

.add-hint-fade-enter-from,
.add-hint-fade-leave-to {
    opacity: 0;
    transform: translateX(-50%) translateY(12px);
}

.modal-backdrop-custom {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
}

.event-modal {
    width: min(520px, 94vw);
    border-radius: 18px;
    border: none;
    background: #f4f4f4;
}

.event-title {
    font-size: 30px;
    font-weight: 700;
    line-height: 1.05;
    color: #101010;
}

.close-btn {
    border: none;
    background: transparent;
    font-size: 42px;
    line-height: 1;
    color: #4a4a4a;
    padding: 0;
    margin-top: -10px;
}

.event-text {
    font-size: 24px;
    line-height: 1.18;
    color: #1e1e1e;
}

.event-meta {
    color: #9f9f9f;
    font-size: 16px;
}

.pocket-grid {
    border-top: 1px solid #ececec;
    padding-top: 10px;
}

.pocket-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 0;
    gap: 12px;
}

.pocket-key {
    color: #6d6d6d;
    font-size: 13px;
}

.pocket-val {
    font-weight: 600;
    color: #212121;
    font-size: 14px;
    text-align: right;
}

.votes-row {
    display: flex;
    gap: 18px;
    align-items: center;
    justify-content: flex-start;
}

.vote-group {
    display: flex;
    align-items: center;
    gap: 10px;
}

.vote-pill {
    height: 40px;
    min-width: 70px;
    border-radius: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 0 12px;
}

.vote-pill img {
    width: 20px;
    height: 20px;
}

.vote-number {
    font-size: 20px;
    color: #fff;
    font-weight: 700;
    line-height: 1;
}

.vote-pill-up {
    background: #55c64f;
}

.vote-pill-down {
    background: #ff3838;
}

.vote-time {
    font-size: 16px;
    color: #111;
}

.bottom-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.confidence-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
}

.confidence-icon {
    width: 46px;
    height: 46px;
}

.confidence-value {
    font-weight: 700;
    font-size: 38px;
    line-height: 1;
}

.confidence-high {
    color: #38b63f;
}

.confidence-medium {
    color: #ffd502;
}

.confidence-low {
    color: #ef3d3d;
}

.actions-wrap {
    display: flex;
    gap: 10px;
}

.action-btn {
    width: 40px;
    height: 40px;
    border: none;
    border-radius: 12px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 20px;
}

.action-btn-edit {
    background: #f7bb00;
    color: #1f1f1f;
}

.action-btn-delete {
    background: #f2053e;
}

.edit-panel {
    background: #fff;
    border-radius: 10px;
    padding: 8px;
}

@media (max-width: 992px) {
    .event-modal {
        width: 96vw;
        border-radius: 18px;
    }
    .event-title {
        font-size: 28px;
    }
    .close-btn {
        font-size: 48px;
    }
    .event-text {
        font-size: 26px;
    }
    .event-meta {
        font-size: 18px;
    }
    .votes-row {
        flex-direction: column;
        align-items: flex-start;
        gap: 14px;
    }
    .vote-pill {
        height: 56px;
        min-width: 118px;
        border-radius: 28px;
    }
    .vote-pill img {
        width: 22px;
        height: 22px;
    }
    .vote-number {
        font-size: 30px;
    }
    .vote-time {
        font-size: 18px;
    }
    .confidence-icon {
        width: 52px;
        height: 52px;
    }
    .confidence-value {
        font-size: 42px;
    }
    .action-btn {
        width: 58px;
        height: 58px;
        border-radius: 12px;
        font-size: 24px;
    }
}

:deep(.ymaps-2-1-79-controls__control) {
    transform-origin: top right;
}

:deep(.ymaps-2-1-79-controls__control .ymaps-2-1-79-traffic) {
    transform: scale(1);
    transform-origin: top right;
}
</style>
