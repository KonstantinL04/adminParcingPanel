<script setup>
import { onMounted, onUnmounted, ref, computed, watch } from "vue";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";

import defaultEventIcon from "@/assets/default.png";
import cameraIcon from "@/assets/camera.png";
import policeIcon from "@/assets/police.png";
import accidentIcon from "@/assets/accident.png";
import clearIcon from "@/assets/clear.png";
import locationIcon from "@/assets/location.svg";

const mapContainer = ref(null);
const statusText = ref("");

const INITIAL_CENTER = [52.2855, 104.2890];
const INITIAL_ZOOM = 12;

const BASE_CLUSTER_GRID_SIZE = 420;
const ROAD_EVENTS_MIN_ZOOM = 13;
const ZONE_MIN_ZOOM = 15;
const LOAD_MIN_ZOOM = 10;
const EVENT_CACHE_MAX_AREAS = 40;

let map = null;
let ymapsRef = null;
let clusterer = null;
let zoneCollection = null;
let markerStatesMap = new Map();
let markerStates = [];
let clusterLayoutClass = null;
let clusterUpdateTimer = null;
let bboxLoadTimer = null;
let isClustererOnMap = false;
let lastLoadedBbox = null;
let loadedEventBboxes = [];
let cachedEventPoints = new Map();

let dimMapObjects = false;
let dimForEdit = false;
const auth = useAuthStore();

const currentZoom = ref(INITIAL_ZOOM);
const shouldShowRoadEvents = computed(() => currentZoom.value >= ROAD_EVENTS_MIN_ZOOM);
const showZoomMessage = computed(() => !shouldShowRoadEvents.value);

const isLoading = ref(true);
const isBboxLoading = ref(false);
const clusterModeActive = ref(true);
const showPointModal = ref(false);
const selectedPointState = ref(null);
const isEditMode = ref(false);
const isMovingMarker = ref(false);
const showMoveMarkerPanel = ref(false);
const editForm = ref({
  class_item: null,
  confirmations: 0,
  denials: 0,
  speed_limit: 0,
  direction: 0,
  dir_type: 1,
  distance: 0,
  angle: 0,
  lat: 0,
  lon: 0,
});
const modalBusy = ref(false);
const modalError = ref("");
const modalSuccess = ref("");
const eventMedia = ref([]);
const mediaUploadFile = ref(null);
const photoInput = ref(null);
const voteBusy = ref(false);
const showAddPanel = ref(false);
const addStep = ref(1);
const addBusy = ref(false);
const addError = ref("");
const addForm = ref({
  lat: 0,
  lon: 0,
  class_item: null,
  speed_limit: 60,
  direction: 0,
  dir_type: 1,
  distance: 300,
  angle: 25,
  details: "",
});
const addCatalog = ref([]);
const addClassPage = ref(0);
const addItemPage = ref(0);
const selectedEventClass = ref(null);
const selectedEventClassItem = ref(null);
let addPlacemark = null;
let editPlacemark = null;

const showEditCategoryDropdown = ref(false);
const editCategorySearch = ref("");
const expandedEditClasses = ref({});

const trafficShown = ref(false);
const trafficLevel = ref(0);
let trafficProvider = null;
let trafficUpdateInterval = null;
let trafficStateListenerAttached = false;

const weatherData = ref(null);
const weatherLoading = ref(false);
const weatherError = ref("");
const showWeatherDetails = ref(false);

const showMapSearch = ref(false);
const mapSearchQuery = ref("");
const mapSearchResults = ref([]);
const mapSearchBusy = ref(false);
const mapSearchError = ref("");
let searchPlacemark = null;
const myLocationLoading = ref(false);
let myLocationPlacemark = null;

const showFilterPanel = ref(false);
const appliedCategoryFilters = ref([]);
const draftCategoryFilters = ref([]);
const filtersInitialized = ref(false);
const expandedFilterClasses = ref({});

const allCatalogItems = ref([]);
const catalogClasses = ref([]);

let addZoneHandles = [];
let addZonePolygon = null;
let editZoneHandles = [];
let editZonePolygon = null;

const currentCategoryName = computed(() => {
  if (!editForm.value.class_item) return "Выберите категорию";
  return getCategoryNameByItemId(editForm.value.class_item) || "Выберите категорию";
});

const currentCategoryIcon = computed(() => {
  if (!editForm.value.class_item) return null;
  return getCategoryIconByItemId(editForm.value.class_item);
});

const pagedEventClasses = computed(() => addCatalog.value.slice(addClassPage.value * 8, (addClassPage.value + 1) * 8));
const canClassPrev = computed(() => addClassPage.value > 0);
const canClassNext = computed(() => (addClassPage.value + 1) * 8 < addCatalog.value.length);

const selectedClassItems = computed(() => selectedEventClass.value?.items || []);
const pagedClassItems = computed(() => selectedClassItems.value.slice(addItemPage.value * 8, (addItemPage.value + 1) * 8));
const canItemPrev = computed(() => addItemPage.value > 0);
const canItemNext = computed(() => (addItemPage.value + 1) * 8 < selectedClassItems.value.length);

function getItemById(itemId) {
  if (!itemId) return null;
  return allCatalogItems.value.find(item => item.id === itemId);
}

function getCategoryNameByItemId(itemId) {
  const item = getItemById(itemId);
  return item?.name || '';
}

function getCategoryIconByItemId(itemId) {
  const item = getItemById(itemId);
  if (item?.icon) return resolveMediaUrl(item.icon);
  const cls = catalogClasses.value.find(c => c.items?.some(i => i.id === itemId));
  if (cls?.icon) return resolveMediaUrl(cls.icon);
  return null;
}

function getEventClassIcon(eventClass) {
  if (eventClass?.icon) return resolveMediaUrl(eventClass.icon);
  const name = String(eventClass?.name || "").toLowerCase();
  if (name.includes("камер")) return cameraIcon;
  if (name.includes("засад") || name.includes("дпс")) return policeIcon;
  if (name.includes("опас")) return accidentIcon;
  if (name.includes("перекры") || name.includes("помощ")) return clearIcon;
  return defaultEventIcon;
}

function getClassItemIcon(item) {
  if (item?.icon) return resolveMediaUrl(item.icon);
  const cls = catalogClasses.value.find(c => c.items?.some(i => i.id === item.id));
  if (cls?.icon) return resolveMediaUrl(cls.icon);
  const name = String(item?.name || "").toLowerCase();
  if (name.includes("скорост")) return cameraIcon;
  if (name.includes("полос")) return policeIcon;
  if (name.includes("размет")) return clearIcon;
  if (name.includes("пешеход")) return accidentIcon;
  return defaultEventIcon;
}

function resolveMediaUrl(path) {
  if (!path) return defaultEventIcon;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return path.startsWith("/") ? path : `/${path}`;
}

function getCurrentUserId() {
  const user = auth.user || {};
  return String(user.id || user.email || user.username || "").trim();
}

function getWeatherSymbol(code) {
  const value = String(code || "").toLowerCase();
  if (value.includes("snow")) return "❄";
  if (value.includes("rain") || value.includes("drizzle")) return "☂";
  if (value.includes("thunderstorm")) return "⚡";
  if (value.includes("cloud")) return "☁";
  if (value.includes("mist") || value.includes("fog") || value.includes("haze")) return "≋";
  return "☀";
}

function formatTemp(value) {
  if (value === null || value === undefined || value === "") return "—";
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return "—";
  return `${numberValue > 0 ? "+" : ""}${Math.round(numberValue)}`;
}

function formatWeatherHour(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(11, 16) || "—";
  return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function getBrowserPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Геолокация недоступна в браузере"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      position => resolve(position),
      error => reject(error),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    );
  });
}

async function loadCurrentWeather() {
  weatherLoading.value = true;
  weatherError.value = "";
  try {
    const position = await getBrowserPosition();
    const lat = position.coords.latitude;
    const lon = position.coords.longitude;
    const { data } = await axios.get("/api/events/weather/current/", {
      params: { lat, lon },
    });
    weatherData.value = data;
  } catch (e) {
    weatherError.value = e?.response?.data?.detail || e?.message || "Не удалось получить погоду";
  } finally {
    weatherLoading.value = false;
  }
}

function toggleMapSearch() {
  showMapSearch.value = !showMapSearch.value;
  if (showMapSearch.value) {
    showWeatherDetails.value = false;
    setTimeout(() => document.querySelector(".map-search-input")?.focus(), 180);
  }
}

async function performMapSearch() {
  const query = mapSearchQuery.value.trim();
  if (!query) {
    mapSearchResults.value = [];
    mapSearchError.value = "";
    return;
  }
  if (!ymapsRef) {
    mapSearchError.value = "Карта еще загружается";
    return;
  }

  mapSearchBusy.value = true;
  mapSearchError.value = "";
  try {
    let rows = [];
    try {
      const result = await ymapsRef.geocode(query, { results: 6 });
      result.geoObjects.each((geoObject) => {
        const meta = geoObject.properties.get("metaDataProperty")?.GeocoderMetaData || {};
        const coords = geoObject.geometry.getCoordinates();
        rows.push({
          title: geoObject.properties.get("name") || meta.text || query,
          subtitle: meta.text || "",
          coords,
        });
      });
    } catch (e) {
      const { data } = await axios.get("/api/events/map-search/search/", {
        params: { q: query },
      });
      rows = Array.isArray(data?.results) ? data.results : [];
    }
    mapSearchResults.value = rows;
    if (!rows.length) mapSearchError.value = "Ничего не найдено";
  } catch (e) {
    mapSearchError.value = "Не удалось выполнить поиск";
  } finally {
    mapSearchBusy.value = false;
  }
}

function selectMapSearchResult(result) {
  if (!map || !ymapsRef || !result?.coords) return;
  map.setCenter(result.coords, 12, { duration: 350 });
  if (searchPlacemark) {
    map.geoObjects.remove(searchPlacemark);
  }
  searchPlacemark = new ymapsRef.Placemark(result.coords, {
    hintContent: result.title,
    balloonContent: result.subtitle || result.title,
  }, {
    preset: "islands#blueSearchIcon",
  });
  map.geoObjects.add(searchPlacemark);
  mapSearchQuery.value = result.title;
  mapSearchResults.value = [];
  showMapSearch.value = false;
}

async function focusMyLocation() {
  if (!map || !ymapsRef || myLocationLoading.value) return;
  myLocationLoading.value = true;
  try {
    const position = await getBrowserPosition();
    const coords = [position.coords.latitude, position.coords.longitude];
    if (myLocationPlacemark) {
      myLocationPlacemark.geometry.setCoordinates(coords);
    } else {
      myLocationPlacemark = new ymapsRef.Placemark(coords, {
        hintContent: "Моя геопозиция",
      }, {
        preset: "islands#blueCircleDotIcon",
        zIndex: 10000,
      });
      map.geoObjects.add(myLocationPlacemark);
    }
    const targetZoom = Math.max(map.getZoom(), ROAD_EVENTS_MIN_ZOOM + 2);
    currentZoom.value = targetZoom;
    map.setCenter(coords, targetZoom, { duration: 350 });
    setTimeout(() => loadPointsByBbox(), 450);
  } catch (e) {
    statusText.value = e?.message || "Не удалось определить геопозицию";
  } finally {
    myLocationLoading.value = false;
  }
}

async function loadEventDetails(eventId) {
  if (!eventId) return;
  try {
    const { data } = await axios.get(`/api/events/events/${eventId}/`);
    eventMedia.value = Array.isArray(data?.media) ? data.media : [];
    editForm.value.confirmations = Number(data?.confirmations || 0);
    editForm.value.denials = Number(data?.denials || 0);
  } catch {
    eventMedia.value = [];
  }
}

function onMediaFileChange(e) {
  mediaUploadFile.value = e.target.files?.[0] || null;
}

async function onMediaFilePicked(e) {
  onMediaFileChange(e);
  if (mediaUploadFile.value) {
    await uploadEventMedia();
  }
  if (e?.target) e.target.value = "";
}

function formatRelativeTime(value) {
  if (!value) return "недавно";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "недавно";
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.max(0, Math.floor(diffMs / 60000));
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} час назад`;
  const days = Math.floor(hours / 24);
  return `${days} дн назад`;
}

function getEventReliabilityLabel() {
  const score = Number(editForm.value.confirmations || 0) - Number(editForm.value.denials || 0);
  if (score >= 3) return "Высокая";
  if (score <= -3) return "Низкая";
  return "Средняя";
}

function getEventReliabilityClass() {
  const label = getEventReliabilityLabel();
  if (label === "Высокая") return "high";
  if (label === "Низкая") return "low";
  return "medium";
}

function getSelectedEventTitle() {
  return getCategoryNameByItemId(selectedPointState.value?.point?.class_item) || "Категория события";
}

function getSelectedEventDetails() {
  const point = selectedPointState.value?.point || {};
  const category = getSelectedEventTitle();
  const speed = Number(editForm.value.speed_limit || point.speed_limit || 0);
  const details = point.details || "";
  if (details && speed) return `${speed} км/ч, ${details}`;
  if (details) return details;
  if (speed) return `Скорость ${speed} км/ч`;
  return category;
}

function getSelectedEventMeta() {
  const point = selectedPointState.value?.point || {};
  const time = formatRelativeTime(point.last_seen_at || point.first_seen_at);
  const author = point.user_id || "имя автора";
  const source = point.source_name || point.source || "источник";
  return `${time}, ${author}, ${source}`;
}

async function uploadEventMedia() {
  const eventId = selectedPointState.value?.point?.id;
  const userId = getCurrentUserId();
  if (!eventId || !mediaUploadFile.value || !userId) {
    modalError.value = "Нужны файл и авторизованный пользователь";
    return;
  }
  try {
    modalBusy.value = true;
    const fd = new FormData();
    fd.append("image", mediaUploadFile.value);
    fd.append("user_id", userId);
    await axios.post(`/api/events/events/${eventId}/upload-media/`, fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    mediaUploadFile.value = null;
    await loadEventDetails(eventId);
  } catch (e) {
    modalError.value = e?.response?.data?.detail || "Не удалось загрузить фото";
  } finally {
    modalBusy.value = false;
  }
}

async function deleteEventMedia(mediaId) {
  const eventId = selectedPointState.value?.point?.id;
  if (!eventId || !mediaId) return;
  try {
    modalBusy.value = true;
    await axios.delete(`/api/events/events/${eventId}/delete-media/${mediaId}/`);
    await loadEventDetails(eventId);
  } catch (e) {
    modalError.value = e?.response?.data?.detail || "Не удалось удалить фото";
  } finally {
    modalBusy.value = false;
  }
}

async function voteForEvent(vote) {
  const eventId = selectedPointState.value?.point?.id;
  const userId = getCurrentUserId();
  if (!eventId || !userId) {
    modalError.value = "Нужен авторизованный пользователь";
    return;
  }
  try {
    voteBusy.value = true;
    const { data } = await axios.post(`/api/events/events/${eventId}/vote/`, {
      user_id: userId,
      vote,
      lat: Number(editForm.value.lat),
      lon: Number(editForm.value.lon),
    });
    editForm.value.confirmations = Number(data?.confirmations || 0);
    editForm.value.denials = Number(data?.denials || 0);
    if (selectedPointState.value?.point) {
      selectedPointState.value.point.confirmations = editForm.value.confirmations;
      selectedPointState.value.point.denials = editForm.value.denials;
    }
    modalSuccess.value = "Голос учтён";
    modalError.value = "";
  } catch (e) {
    modalError.value = e?.response?.data?.detail || "Не удалось проголосовать";
  } finally {
    voteBusy.value = false;
  }
}

function categoryKeyForPoint(point) {
  if (point?.class_item) return `cat:${point.class_item}`;
  return "cat:other";
}

function getPlacemarkCategoryKey(geoObject) {
  return geoObject?.properties?.get?.("category_key") || "other";
}

function getPlacemarkIcon(geoObject) {
  return geoObject?.properties?.get?.("category_icon") || defaultEventIcon;
}

function applyPlacemarkIcon(placemark, iconHref, isDraggable = false) {
  if (!placemark) return;
  const safeIcon = iconHref || defaultEventIcon;
  placemark.options.set("iconLayout", "default#image");
  placemark.options.set("iconImageHref", safeIcon);
  const [w, h] = isDraggable ? [32, 32] : [24, 24];
  placemark.options.set("iconImageSize", [w, h]);
  placemark.options.set("iconImageOffset", [-w / 2, -h]);
  placemark.options.set("iconShape", isDraggable ? { type: "Rectangle", coordinates: [[-w / 2, -h], [w / 2, 0]] } : null);
}

function createPlacemark(point, lat, lon, icon, draggable = false) {
  let finalIcon = defaultEventIcon;
  if (point.class_item) {
    const itemIcon = getCategoryIconByItemId(point.class_item);
    if (itemIcon) finalIcon = itemIcon;
  }
  if (finalIcon === defaultEventIcon && icon && icon !== defaultEventIcon) finalIcon = icon;

  const [w, h] = draggable ? [32, 32] : [24, 24];
  const placemark = new ymapsRef.Placemark([lat, lon], {
    category_key: categoryKeyForPoint(point),
    category_icon: finalIcon,
  }, {
    draggable, dragCursor: "move", cursor: draggable ? "move" : "pointer",
    interactivityModel: "default#geoObject", pane: "places",
    zIndex: draggable ? 10000 : 0, zIndexHover: draggable ? 10001 : 1, zIndexActive: draggable ? 10002 : 1,
    hasBalloon: false, openBalloonOnClick: false,
    iconLayout: "default#image", iconImageHref: finalIcon,
    iconImageSize: [w, h], iconImageOffset: [-w / 2, -h],
    iconShape: draggable ? { type: "Rectangle", coordinates: [[-w / 2, -h], [w / 2, 0]] } : undefined,
  });
  applyPlacemarkIcon(placemark, finalIcon, draggable);
  return placemark;
}

function updatePlacemarkMeta(placemark, point, icon, isDraggable = false) {
  if (!placemark) return;
  let finalIcon = icon || defaultEventIcon;
  if (point.class_item) {
    const itemIcon = getCategoryIconByItemId(point.class_item);
    if (itemIcon) finalIcon = itemIcon;
  }
  applyPlacemarkIcon(placemark, finalIcon, isDraggable);
  placemark.properties.set("category_key", categoryKeyForPoint(point));
  placemark.properties.set("category_icon", finalIcon);
}

function setPlacemarkDimmed(placemark, dimmed) {
  if (!placemark?.options) return;
  const opacity = dimmed ? 0.28 : 1;
  placemark.options.set("iconOpacity", opacity);
  placemark.options.set("iconImageOpacity", opacity);
  placemark.options.set("opacity", opacity);
}

function loadYandexMaps() {
  return new Promise((resolve, reject) => {
    if (window.ymaps) { window.ymaps.ready(() => resolve(window.ymaps)); return; }
    const apiKey = import.meta.env.VITE_YANDEX_MAPS_API_KEY;
    const script = document.createElement("script");
    script.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`;
    script.async = true;
    script.onload = () => window.ymaps.ready(() => resolve(window.ymaps));
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

function createClusterLayout(ymaps) {
  return ymaps.templateLayoutFactory.createClass("<div></div>", {
    build() {
      this.constructor.superclass.build.call(this);
      const geoObjects = this.getData()?.properties?.get("geoObjects") || [];
      const groupsMap = new Map();
      for (const geoObject of geoObjects) {
        const key = getPlacemarkCategoryKey(geoObject);
        const icon = getPlacemarkIcon(geoObject);
        const group = groupsMap.get(key) || { count: 0, icon };
        group.count += 1;
        groupsMap.set(key, group);
      }
      const allGroups = Array.from(groupsMap.values()).sort((a, b) => b.count - a.count);
      const zoom = Number(this.getData()?.geoObject?.getMap?.()?.getZoom?.());
      const isFarZoom = zoom <= 11, isMidZoom = zoom > 11 && zoom <= 13;
      const maxItemsPerRow = isFarZoom ? 3 : isMidZoom ? 4 : 5;
      const maxVisibleGroups = isFarZoom ? 6 : isMidZoom ? 8 : 12;
      const groups = allGroups.slice(0, maxVisibleGroups);
      const hidden = Math.max(0, allGroups.length - groups.length);
      const itemWidth = isFarZoom ? 42 : 46, rowHeight = isFarZoom ? 22 : 24;
      const rows = [];
      for (let i = 0; i < groups.length; i += maxItemsPerRow) rows.push(groups.slice(i, i + maxItemsPerRow));
      if (hidden > 0) {
        const tail = { count: `+${hidden}`, icon: null };
        if (!rows.length || rows[rows.length - 1].length >= maxItemsPerRow) rows.push([tail]);
        else rows[rows.length - 1].push(tail);
      }
      const cols = Math.min(maxItemsPerRow, groups.length || 1);
      this._width = Math.max(68, cols * itemWidth + 12);
      this._height = Math.max(30, rows.length * rowHeight + 8);
      const dimmed = dimMapObjects || dimForEdit;
      const rowsHtml = rows.map((row) => `<div style="display:flex;align-items:center;justify-content:center;gap:8px;min-height:${rowHeight}px;">${row.map((g) => `<div style="display:flex;align-items:center;gap:5px;min-width:${itemWidth - 6}px;justify-content:center;">${g.icon ? `<img src="${g.icon}" style="width:14px;height:14px;" />` : ""}<span style="font-size:13px;font-weight:700;color:#111;">${g.count}</span></div>`).join("")}</div>`).join("");
      this.getParentElement().innerHTML = `<div style="width:${this._width}px;height:${this._height}px;border-radius:15px;background:#fff;box-shadow:0 4px 16px rgba(0,0,0,.22);opacity:${dimmed ? 0.35 : 1};display:flex;flex-direction:column;align-items:center;justify-content:center;padding:4px 6px;transform:translate(-50%,-50%);">${rowsHtml}</div>`;
    },
    clear() { this.getParentElement().innerHTML = ""; this.constructor.superclass.clear.call(this); },
    getShape() {
      return new ymaps.shape.Rectangle(new ymaps.geometry.pixel.Rectangle([[- (this._width || 120) / 2, - (this._height || 64) / 2], [(this._width || 120) / 2, (this._height || 64) / 2]]));
    },
  });
}

function calcClusterGridSizeByZoom(zoom) {
  const z = Number(zoom);
  if (z <= 7) return 1400; if (z <= 8) return 1320; if (z <= 9) return 1240;
  if (z <= 10) return 1120; if (z <= 11) return 980; if (z <= 12) return 820;
  if (z <= 13) return 680; if (z <= 14) return 560;
  return BASE_CLUSTER_GRID_SIZE;
}

function createClusterer() {
  clusterLayoutClass = createClusterLayout(ymapsRef);
  clusterer = new ymapsRef.Clusterer({
    clusterIconLayout: clusterLayoutClass, groupByCoordinates: false,
    gridSize: BASE_CLUSTER_GRID_SIZE, minClusterSize: 2,
    clusterDisableClickZoom: false, clusterOpenBalloonOnClick: false,
  });
  map.geoObjects.add(clusterer);
  isClustererOnMap = true;
  clusterer.options.set("gridSize", calcClusterGridSizeByZoom(map.getZoom()));
}

function normalizeAngle360(value) { const n = Number(value); if (!Number.isFinite(n)) return 0; return ((n % 360) + 360) % 360; }

function destinationByDistanceAndBearing(lat, lon, bearingDeg, distanceM) {
  const R = 6378137; const brng = (bearingDeg * Math.PI) / 180; const d = Number(distanceM) / R;
  const lat1 = (lat * Math.PI) / 180; const lon1 = (lon * Math.PI) / 180;
  const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(brng));
  const lon2 = lon1 + Math.atan2(Math.sin(brng) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2));
  return [(lat2 * 180) / Math.PI, (lon2 * 180) / Math.PI];
}

function calculateBearing(lat1, lon1, lat2, lon2) {
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const lat1Rad = lat1 * Math.PI / 180, lat2Rad = lat2 * Math.PI / 180;
  const y = Math.sin(dLon) * Math.cos(lat2Rad);
  const x = Math.cos(lat1Rad) * Math.sin(lat2Rad) - Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon);
  return normalizeAngle360(Math.atan2(y, x) * 180 / Math.PI);
}

function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180, dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function buildSectorPoints(lat, lon, centerAzimuth, angleDeg, distanceM) {
  const distance = Math.max(10, Math.min(Number(distanceM), 10000));
  const angle = Math.max(5, Math.min(360, Number(angleDeg) || 60));
  const steps = Math.max(12, Math.min(48, Math.round(angle / 4)));
  const start = normalizeAngle360(centerAzimuth - angle / 2);
  const end = normalizeAngle360(centerAzimuth + angle / 2);
  const diff = start <= end ? end - start : 360 - (start - end);
  const points = [[lat, lon]];
  for (let i = 0; i <= steps; i++) points.push(destinationByDistanceAndBearing(lat, lon, normalizeAngle360(start + (diff * i) / steps), distance));
  points.push([lat, lon]);
  return points;
}

function drawZones() {
  if (!map || !zoneCollection) return;
  try { zoneCollection.removeAll(); } catch (e) { return; }
  if (!shouldShowRoadEvents.value || map.getZoom() < ZONE_MIN_ZOOM) return;
  if (showMoveMarkerPanel.value) return;
  const itemsToDraw = [...markerStates];
  for (const item of itemsToDraw) {
    if (!item.visible) continue;
    const isEditingSelected = isEditMode.value && selectedPointState.value === item;
    if (clusterModeActive.value && !isEditingSelected && !showAddPanel.value && !dimForEdit) {
      try {
        const state = clusterer ? clusterer.getObjectState(item.placemark) : null;
        if (state && (!state.isShown || state.isClustered)) continue;
      } catch (e) { continue; }
    }
    if (dimForEdit && item !== selectedPointState.value) continue;
    const zoneLat = isEditingSelected ? Number(editForm.value.lat) : item.lat;
    const zoneLon = isEditingSelected ? Number(editForm.value.lon) : item.lon;
    if (!Number.isFinite(zoneLat) || !Number.isFinite(zoneLon)) continue;
    const p = item.point;
    const zoneDirection = isEditingSelected ? Number(editForm.value.direction || 0) : Number(p.direction || 0);
    const zoneAngle = isEditingSelected ? Number(editForm.value.angle || 0) : Number(p.angle || 0);
    const zoneDistance = isEditingSelected ? Number(editForm.value.distance || 0) : Number(p.distance || 0);
    const zoneDirType = isEditingSelected ? Number(editForm.value.dir_type || 1) : Number(p.dir_type || 1);
    if (!Number.isFinite(zoneDistance) || zoneDistance <= 0) continue;
    const dimmed = showAddPanel.value || dimForEdit;
    const addZone = (direction) => {
      try {
        const points = buildSectorPoints(zoneLat, zoneLon, direction, zoneAngle, zoneDistance);
        zoneCollection.add(new ymapsRef.GeoObject(
          { geometry: { type: "Polygon", coordinates: [points] } },
          { fillColor: dimmed ? "rgba(33,150,243,.08)" : "rgba(33,150,243,.22)", strokeColor: dimmed ? "rgba(33,150,243,.28)" : "rgba(33,150,243,.55)", strokeWidth: 1.5, interactivityModel: "default#silent", pane: "areas", zIndex: 0 }
        ));
      } catch (e) { }
    };
    addZone(zoneDirection);
    if (zoneDirType === 2) addZone(zoneDirection + 180);
  }
}

function ensureFilterState() {
  const keys = allCatalogItems.value.map(item => `cat:${item.id}`).filter(k => k !== 'cat:');
  if (!keys.length) return;
  if (!filtersInitialized.value) { appliedCategoryFilters.value = [...keys]; draftCategoryFilters.value = [...keys]; filtersInitialized.value = true; return; }
  const keysSet = new Set(keys);
  if (appliedCategoryFilters.value.length > 0) {
    const newKeys = keys.filter(k => !appliedCategoryFilters.value.includes(k));
    if (newKeys.length) { appliedCategoryFilters.value = [...appliedCategoryFilters.value, ...newKeys]; draftCategoryFilters.value = [...draftCategoryFilters.value, ...newKeys]; }
    appliedCategoryFilters.value = appliedCategoryFilters.value.filter(k => keysSet.has(k));
    draftCategoryFilters.value = draftCategoryFilters.value.filter(k => keysSet.has(k));
  }
}

function toggleFilterPanel() { showFilterPanel.value ? showFilterPanel.value = false : (draftCategoryFilters.value = [...appliedCategoryFilters.value], showFilterPanel.value = true); }
function toggleFilterClass(classId) { expandedFilterClasses.value[classId] = !expandedFilterClasses.value[classId]; }
function toggleDraftCategory(key) {
  const set = new Set(draftCategoryFilters.value);
  set.has(key) ? set.delete(key) : set.add(key);
  draftCategoryFilters.value = allCatalogItems.value.map(item => `cat:${item.id}`).filter(k => set.has(k));
}
function applyCategoryFilters() { appliedCategoryFilters.value = [...draftCategoryFilters.value]; showFilterPanel.value = false; rebuildVisibleObjects(); }
function resetCategoryFilters() {
  const keys = allCatalogItems.value.map(item => `cat:${item.id}`).filter(k => k !== 'cat:');
  draftCategoryFilters.value = [...keys]; appliedCategoryFilters.value = [...keys];
  showFilterPanel.value = false; rebuildVisibleObjects();
}
function toggleDraftClass(classItems) {
  if (!classItems || !classItems.length) return;
  const itemKeys = classItems.map(item => `cat:${item.id}`);
  const allSelected = itemKeys.every(key => draftCategoryFilters.value.includes(key));
  if (allSelected) { draftCategoryFilters.value = draftCategoryFilters.value.filter(k => !itemKeys.includes(k)); }
  else { const set = new Set([...draftCategoryFilters.value, ...itemKeys]); draftCategoryFilters.value = allCatalogItems.value.map(item => `cat:${item.id}`).filter(k => set.has(k)); }
}
function disableAllFilters() { draftCategoryFilters.value = []; }
function enableAllFilters() { const keys = allCatalogItems.value.map(item => `cat:${item.id}`).filter(k => k !== 'cat:'); draftCategoryFilters.value = [...keys]; }
function isClassFullySelected(classItems) { if (!classItems || !classItems.length) return false; return classItems.map(item => `cat:${item.id}`).every(key => draftCategoryFilters.value.includes(key)); }
function isClassPartiallySelected(classItems) {
  if (!classItems || !classItems.length) return false;
  const itemKeys = classItems.map(item => `cat:${item.id}`);
  const selectedCount = itemKeys.filter(key => draftCategoryFilters.value.includes(key)).length;
  return selectedCount > 0 && selectedCount < itemKeys.length;
}
function toggleClusterMode() { clusterModeActive.value = !clusterModeActive.value; rebuildVisibleObjects(); }
function getTrafficClass(level) {
  if (level >= 0 && level <= 3) return 'traffic-green';
  if (level >= 4 && level <= 6) return 'traffic-yellow';
  return 'traffic-red';
}

function normalizeTrafficLevel(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return Math.max(0, Math.min(10, Math.round(n)));
}

function readTrafficLevel() {
  const state = trafficProvider?.state;
  const rawLevel = typeof state?.get === "function" ? state.get("level") : state?.level;
  const level = normalizeTrafficLevel(rawLevel);
  if (level !== null) trafficLevel.value = level;
  return level;
}

function ensureTrafficProvider() {
  if (!trafficProvider) trafficProvider = new ymapsRef.traffic.provider.Actual({ map });
  if (!trafficStateListenerAttached && trafficProvider?.state?.events?.add) {
    trafficProvider.state.events.add("change", () => readTrafficLevel());
    trafficStateListenerAttached = true;
  }
  return trafficProvider;
}

async function updateTrafficLevel() {
  if (!ymapsRef || !map) return;
  try {
    ensureTrafficProvider();
    if (typeof trafficProvider.update === "function") await trafficProvider.update();
    if (readTrafficLevel() === null) {
      setTimeout(readTrafficLevel, 600);
    }
  } catch (e) { trafficLevel.value = 0; }
}

function toggleTraffic() {
  trafficShown.value = !trafficShown.value;
  if (trafficShown.value) {
    ensureTrafficProvider();
    trafficProvider.setMap(map);
    updateTrafficLevel();
    trafficUpdateInterval = setInterval(updateTrafficLevel, 120000);
  } else {
    if (trafficProvider) trafficProvider.setMap(null);
    if (trafficUpdateInterval) { clearInterval(trafficUpdateInterval); trafficUpdateInterval = null; }
    trafficLevel.value = 0;
  }
}

function focusMapOnPoint(state) {
  if (!map || !state) return;
  const coords = [state.lat, state.lon];
  if (!coords.every(Number.isFinite)) return;
  requestAnimationFrame(() => {
    try { map.container.fitToViewport(); currentZoom.value = Math.max(map.getZoom(), ZONE_MIN_ZOOM + 1); map.setCenter(coords, currentZoom.value); setTimeout(drawZones, 0); }
    catch (e) { console.error("focusMapOnPoint:", e); }
  });
}

function getEditIcon() { return getCategoryIconByItemId(editForm.value.class_item) || defaultEventIcon; }

function createZoneDragHandler(formRef) {
  return (e, index, type) => {
    const coords = e.get('target').geometry.getCoordinates();
    if (!Array.isArray(coords) || coords.length !== 2) return;
    const lat = Number(formRef.lat), lon = Number(formRef.lon);
    const bearing = calculateBearing(lat, lon, coords[0], coords[1]);
    const d = calculateDistance(lat, lon, coords[0], coords[1]);
    if (type === 'angle') {
      const cDir = Number(formRef.direction || 0), cAng = Number(formRef.angle || 25);
      if (index === 0) {
        const rightEdge = normalizeAngle360(cDir + cAng / 2);
        let diff = normalizeAngle360(rightEdge - bearing);
        if (diff > 180) diff = 360 - diff;
        formRef.angle = Math.max(5, Math.min(180, Math.round(diff)));
      } else {
        const leftEdge = normalizeAngle360(cDir - cAng / 2);
        let diff = normalizeAngle360(bearing - leftEdge);
        if (diff > 180) diff = 360 - diff;
        formRef.angle = Math.max(5, Math.min(180, Math.round(diff)));
      }
    } else { formRef.distance = Math.max(50, Math.min(2000, Math.round(d))); formRef.direction = Math.round(bearing); }
  };
}

function createZoneHandlesForCoords(lat, lon, direction, angle, distance, onDrag) {
  const handles = [];
  if (!map || !ymapsRef) return handles;
  const baseStyle = {
    iconLayout: 'default#image',
    iconImageHref: 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><circle cx="10" cy="10" r="9" fill="white" stroke="#1976d2" stroke-width="2"/></svg>'),
    iconImageSize: [20, 20], iconImageOffset: [-10, -10], cursor: 'pointer', interactivityModel: 'default#geoObject', zIndex: 1000,
  };
  const leftPt = destinationByDistanceAndBearing(lat, lon, normalizeAngle360(direction - angle / 2), distance);
  const left = new ymapsRef.Placemark(leftPt, {}, { ...baseStyle, draggable: true });
  left.events.add('drag', e => onDrag(e, 0, 'angle')); handles.push(left);
  const rightPt = destinationByDistanceAndBearing(lat, lon, normalizeAngle360(direction + angle / 2), distance);
  const right = new ymapsRef.Placemark(rightPt, {}, { ...baseStyle, draggable: true });
  right.events.add('drag', e => onDrag(e, 1, 'angle')); handles.push(right);
  const midPt = destinationByDistanceAndBearing(lat, lon, direction, distance);
  const mid = new ymapsRef.Placemark(midPt, {}, {
    ...baseStyle, draggable: true,
    iconImageHref: 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><circle cx="12" cy="12" r="11" fill="white" stroke="#ff9800" stroke-width="2.5"/><line x1="8" y1="12" x2="16" y2="12" stroke="#ff9800" stroke-width="2"/></svg>'),
    iconImageSize: [24, 24], iconImageOffset: [-12, -12],
  });
  mid.events.add('drag', e => onDrag(e, 2, 'distance')); handles.push(mid);
  return handles;
}

function updateZoneHandlePositions(handles, lat, lon, direction, angle, distance) {
  if (handles.length < 3) return;
  handles[0].geometry.setCoordinates(destinationByDistanceAndBearing(lat, lon, normalizeAngle360(direction - angle / 2), distance));
  handles[1].geometry.setCoordinates(destinationByDistanceAndBearing(lat, lon, normalizeAngle360(direction + angle / 2), distance));
  handles[2].geometry.setCoordinates(destinationByDistanceAndBearing(lat, lon, direction, distance));
}

function updateZonePolygon(polygon, lat, lon, direction, angle, distance, dirType = 1) {
  if (!polygon || !map) return;
  const points1 = buildSectorPoints(lat, lon, direction, angle, distance);
  let allPoints;
  if (dirType === 2) { const points2 = buildSectorPoints(lat, lon, normalizeAngle360(direction + 180), angle, distance); allPoints = [...points1.slice(0, -1), [lat, lon], ...points2.slice(1)]; }
  else { allPoints = points1; }
  polygon.geometry.setCoordinates([allPoints]);
}

function createZoneForForm(formRef) {
  const lat = Number(formRef.lat), lon = Number(formRef.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || !map || !ymapsRef) return null;
  const dir = Number(formRef.direction || 0), ang = Number(formRef.angle || 25), dist = Number(formRef.distance || 300);
  const polygon = new ymapsRef.GeoObject(
    { geometry: { type: "Polygon", coordinates: [buildSectorPoints(lat, lon, dir, ang, dist)] } },
    { fillColor: "rgba(33,150,243,.22)", strokeColor: "rgba(33,150,243,.55)", strokeWidth: 1.5, interactivityModel: "default#silent", pane: "areas", zIndex: 0 }
  );
  map.geoObjects.add(polygon);
  updateZonePolygon(polygon, lat, lon, dir, ang, dist, formRef.dir_type);
  const dragHandler = createZoneDragHandler(formRef);
  const handles = createZoneHandlesForCoords(lat, lon, dir, ang, dist, dragHandler);
  handles.forEach(h => map.geoObjects.add(h));
  return { polygon, handles };
}

function createAddZone() {
  if (addZonePolygon && map) map.geoObjects.remove(addZonePolygon);
  addZoneHandles.forEach(h => { if (map) map.geoObjects.remove(h); });
  addZoneHandles = []; addZonePolygon = null;
  const result = createZoneForForm(addForm.value);
  if (result) { addZonePolygon = result.polygon; addZoneHandles = result.handles; }
}

function clearAddZone() {
  if (addZoneHandles && addZoneHandles.length) { addZoneHandles.forEach(h => { try { if (map && h) map.geoObjects.remove(h); } catch (e) { } }); addZoneHandles = []; }
  if (addZonePolygon) { try { if (map) map.geoObjects.remove(addZonePolygon); } catch (e) { } addZonePolygon = null; }
}

function createEditZone() {
  if (editZonePolygon && map) map.geoObjects.remove(editZonePolygon);
  editZoneHandles.forEach(h => { if (map) map.geoObjects.remove(h); });
  editZoneHandles = []; editZonePolygon = null;
  const result = createZoneForForm(editForm.value);
  if (result) { editZonePolygon = result.polygon; editZoneHandles = result.handles; }
}

function clearEditZone() {
  if (editZoneHandles && editZoneHandles.length) { editZoneHandles.forEach(h => { try { if (map && h) map.geoObjects.remove(h); } catch (e) { } }); editZoneHandles = []; }
  if (editZonePolygon) { try { if (map) map.geoObjects.remove(editZonePolygon); } catch (e) { } editZonePolygon = null; }
}

function onMapWheel(e) {
  if (!isEditMode.value || showMoveMarkerPanel.value) return;
  e.preventDefault(); e.stopPropagation();
  const delta = e.deltaY > 0 ? 5 : -5;
  editForm.value.direction = normalizeAngle360(Number(editForm.value.direction) + delta);
}

function openPointModal(pointState) {
  if (showAddPanel.value) return;
  selectedPointState.value = pointState;
  const p = pointState.point;
  editForm.value = {
    class_item: Number(p.class_item) || null,
    confirmations: Number(p.confirmations || 0),
    denials: Number(p.denials || 0),
    speed_limit: Number(p.speed_limit || 0),
    direction: Number(p.direction || 0),
    dir_type: Number(p.dir_type || 1),
    distance: Number(p.distance || 0),
    angle: Number(p.angle || 25),
    lat: Number(pointState.lat),
    lon: Number(pointState.lon)
  };
  modalError.value = "";
  isEditMode.value = false;
  isMovingMarker.value = false;
  showMoveMarkerPanel.value = false;
  showPointModal.value = true;
  loadEventDetails(p.id);
}

function closePointModal() {
  if (isEditMode.value) {
    isEditMode.value = false;
    dimForEdit = false;
    isMovingMarker.value = false;
    showMoveMarkerPanel.value = false;
    mapContainer.value?.removeEventListener('wheel', onMapWheel);
    clearEditZone();
    if (editPlacemark) { try { if (map) map.geoObjects.remove(editPlacemark); } catch (e) { } editPlacemark = null; }
  }
  showPointModal.value = false;
  selectedPointState.value = null;
  modalBusy.value = false;
  modalError.value = "";
  modalSuccess.value = "";
  eventMedia.value = [];
  mediaUploadFile.value = null;
  voteBusy.value = false;
  setTimeout(() => { try { rebuildVisibleObjects(); } catch (e) { } }, 100);
}

function closeAddPanel() {
  showAddPanel.value = false;
  dimMapObjects = false;
  addStep.value = 1; addBusy.value = false; addError.value = "";
  if (addPlacemark && map) map.geoObjects.remove(addPlacemark);
  addPlacemark = null;
  clearAddZone();
  rebuildVisibleObjects(); drawZones();
}

function openAddPanel() {
  if (showPointModal.value) closePointModal();
  addError.value = ""; addStep.value = 1; addClassPage.value = 0; addItemPage.value = 0;
  selectedEventClass.value = null; selectedEventClassItem.value = null;
  showAddPanel.value = true; dimMapObjects = true;
  rebuildVisibleObjects(); drawZones();
}

function setAddPoint(lat, lon) {
  addForm.value.lat = Number(lat); addForm.value.lon = Number(lon);
  if (!Number.isFinite(addForm.value.lat) || !Number.isFinite(addForm.value.lon)) return;
  if (addPlacemark && map) map.geoObjects.remove(addPlacemark);
  addPlacemark = createPlacemark({ class_item: null }, addForm.value.lat, addForm.value.lon, defaultEventIcon, false);
  if (map) map.geoObjects.add(addPlacemark);
}

function setEditPoint(lat, lon) {
  editForm.value.lat = Number(lat); editForm.value.lon = Number(lon);
  if (!Number.isFinite(editForm.value.lat) || !Number.isFinite(editForm.value.lon)) return;
  if (editPlacemark && map) map.geoObjects.remove(editPlacemark);
  editPlacemark = createPlacemark({ class_item: editForm.value.class_item }, editForm.value.lat, editForm.value.lon, getEditIcon(), true);
  if (map) map.geoObjects.add(editPlacemark);
}

function goAddStep2() {
  if (!Number.isFinite(addForm.value.lat) || !Number.isFinite(addForm.value.lon)) { addError.value = "Сначала выберите точку на карте"; return; }
  addError.value = ""; addStep.value = 2;
}

function selectEventClass(eventClass) { selectedEventClass.value = eventClass; addItemPage.value = 0; addStep.value = 3; }

function selectEventClassItem(item) {
  selectedEventClassItem.value = item;
  addForm.value.class_item = item.id;
  addForm.value.details = item.name || "";
  addStep.value = 4;
  createAddZone();
}

function selectEditCategory(itemId) {
  editForm.value.class_item = Number(itemId);
  showEditCategoryDropdown.value = false;
  if (editPlacemark) {
    const icon = getCategoryIconByItemId(itemId);
    updatePlacemarkMeta(editPlacemark, { class_item: itemId }, icon, true);
  }
  clearEditZone();
  createEditZone();
  drawZones();
}

async function createPoint() {
  if (!selectedEventClassItem.value) { addError.value = "Выберите элемент события"; return; }
  addBusy.value = true; addError.value = "";
  try {
    const item = selectedEventClassItem.value;
    await axios.post("/api/events/events/", {
      location: { type: "Point", coordinates: [Number(addForm.value.lon), Number(addForm.value.lat)] },
      class_item: item.id,
      speed_limit: Number(addForm.value.speed_limit || 0),
      direction: Number(addForm.value.direction || 0),
      dir_type: Number(addForm.value.dir_type || 1),
      distance: Number(addForm.value.distance || 0),
      angle: Number(addForm.value.angle || 0),
      details: addForm.value.details || "",
    });
    invalidateEventCache();
    await loadPointsByBbox();
    closeAddPanel();
  } catch (e) { addError.value = e?.response?.data?.detail || "Не удалось добавить событие"; }
  finally { addBusy.value = false; }
}

function applyPointEditsLocally() {
  if (!selectedPointState.value) return;
  const state = selectedPointState.value, p = state.point;
  p.class_item = Number(editForm.value.class_item) || p.class_item;
  p.speed_limit = Number(editForm.value.speed_limit);
  p.direction = Number(editForm.value.direction);
  p.dir_type = Number(editForm.value.dir_type) === 2 ? 2 : 1;
  p.distance = Number(editForm.value.distance);
  p.angle = Number(editForm.value.angle);
  state.lat = Number(editForm.value.lat);
  state.lon = Number(editForm.value.lon);
  if (p.location) { p.location.coordinates = [state.lon, state.lat]; }
  else { p.location = { type: "Point", coordinates: [state.lon, state.lat] }; }
  try {
    if (state.placemark && state.placemark.geometry && map) {
      state.placemark.geometry.setCoordinates([state.lat, state.lon]);
      const finalIcon = getCategoryIconByItemId(p.class_item) || defaultEventIcon;
      updatePlacemarkMeta(state.placemark, p, finalIcon);
    }
  } catch (e) { }
}

function toggleEditMode(enabled) {
  modalError.value = "";
  const state = selectedPointState.value;
  if (!state?.placemark?.options) return;
  if (enabled) {
    isEditMode.value = true;
    dimForEdit = true;
    showMoveMarkerPanel.value = false;
    editForm.value.lat = state.lat;
    editForm.value.lon = state.lon;
    if (editPlacemark && map) { try { map.geoObjects.remove(editPlacemark); } catch (e) { } editPlacemark = null; }
    editPlacemark = createPlacemark({ class_item: editForm.value.class_item }, editForm.value.lat, editForm.value.lon, getEditIcon(), true);
    if (map) map.geoObjects.add(editPlacemark);
    createEditZone();
    focusMapOnPoint(state);
    rebuildVisibleObjects();
    drawZones();
    mapContainer.value?.addEventListener('wheel', onMapWheel, { passive: false });
  } else {
    isEditMode.value = false;
    dimForEdit = false;
    isMovingMarker.value = false;
    showMoveMarkerPanel.value = false;
    modalSuccess.value = "";
    mapContainer.value?.removeEventListener('wheel', onMapWheel);
    clearEditZone();
    if (editPlacemark) { try { if (map) map.geoObjects.remove(editPlacemark); } catch (e) { } editPlacemark = null; }
    setTimeout(() => { try { rebuildVisibleObjects(); } catch (e) { } }, 100);
  }
}

function startMovingMarker() {
  showMoveMarkerPanel.value = true;
  clearEditZone();
  try { zoneCollection.removeAll(); } catch (e) { }
}

function cancelMovingMarker() {
  showMoveMarkerPanel.value = false;
  createEditZone();
  drawZones();
}

function confirmMovingMarker() {
  showMoveMarkerPanel.value = false;
  createEditZone();
  drawZones();
}

async function savePoint() {
  if (!selectedPointState.value) return;
  modalBusy.value = true;
  modalError.value = "";
  try {
    const state = selectedPointState.value;
    const id = state.point?.id;
    if (id) {
      await axios.patch(`/api/events/events/${id}/`, {
        class_item: Number(editForm.value.class_item) || null,
        speed_limit: Number(editForm.value.speed_limit),
        direction: Number(editForm.value.direction),
        dir_type: Number(editForm.value.dir_type) === 2 ? 2 : 1,
        distance: Number(editForm.value.distance),
        angle: Number(editForm.value.angle),
        location: { type: "Point", coordinates: [Number(editForm.value.lon), Number(editForm.value.lat)] },
      });
    }
    const newKey = categoryKeyForPoint({ class_item: Number(editForm.value.class_item) || state.point.class_item });
    if (appliedCategoryFilters.value.length && !appliedCategoryFilters.value.includes(newKey)) {
      appliedCategoryFilters.value.push(newKey);
      draftCategoryFilters.value.push(newKey);
    }
    isEditMode.value = false;
    dimForEdit = false;
    isMovingMarker.value = false;
    showMoveMarkerPanel.value = false;
    mapContainer.value?.removeEventListener('wheel', onMapWheel);
    clearEditZone();
    if (editPlacemark) { try { if (map) map.geoObjects.remove(editPlacemark); } catch (e) { } editPlacemark = null; }
    applyPointEditsLocally();
    modalSuccess.value = "Событие сохранено";
    rememberCachedPoint(state.point);
    await loadPointsByBbox();
    rebuildVisibleObjects();
  } catch (e) {
    console.error("Save error:", e);
    modalError.value = e?.response?.data?.detail || "Не удалось сохранить событие";
  } finally {
    modalBusy.value = false;
  }
}

async function loadEventCatalog() {
  try {
    const { data } = await axios.get("/api/events/event-classes/catalog/");
    addCatalog.value = Array.isArray(data) ? data : [];
    catalogClasses.value = Array.isArray(data) ? data : [];
    allCatalogItems.value = [];
    for (const cls of catalogClasses.value) { if (cls.items) for (const item of cls.items) allCatalogItems.value.push({ ...item }); }
  } catch (e) { console.error("Ошибка загрузки каталога:", e); }
}

async function archivePoint() {
  if (!selectedPointState.value || !window.confirm("Архивировать это событие?")) return;
  modalBusy.value = true; modalError.value = "";
  const state = selectedPointState.value;
  const id = state.point?.id;
  try { if (id) await axios.post(`/api/events/events/${id}/archive/`); }
  catch (e) { modalError.value = e?.response?.data?.detail || "Не удалось архивировать событие"; modalBusy.value = false; return; }
  markerStatesMap.delete(String(id));
  cachedEventPoints.delete(String(id));
  try { if (state.placemark) { if (clusterer && clusterModeActive.value) clusterer.remove(state.placemark); if (map) map.geoObjects.remove(state.placemark); } } catch (e) { }
  if (editPlacemark) { try { if (map) map.geoObjects.remove(editPlacemark); } catch (e) { } editPlacemark = null; }
  clearEditZone();
  markerStates = markerStates.filter(item => item !== state);
  showPointModal.value = false;
  selectedPointState.value = null;
  isEditMode.value = false;
  dimForEdit = false;
  isMovingMarker.value = false;
  showMoveMarkerPanel.value = false;
  modalBusy.value = false;
  modalError.value = "";
  modalSuccess.value = "";
  mapContainer.value?.removeEventListener('wheel', onMapWheel);
  try { zoneCollection.removeAll(); } catch (e) { }
  await loadPointsByBbox();
  statusText.value = `Точек: ${markerStates.length}`;
}

function rebuildVisibleObjects() {
  if (!map) return;
  currentZoom.value = map.getZoom();
  if (!shouldShowRoadEvents.value) {
    clearRoadEventObjects();
    return;
  }
  try { if (clusterer) clusterer.removeAll(); } catch (e) { }
  const active = new Set(appliedCategoryFilters.value);
  const editingState = isEditMode.value ? selectedPointState.value : null;
  try {
    if (clusterer) {
      if (clusterModeActive.value && !isClustererOnMap) { map.geoObjects.add(clusterer); isClustererOnMap = true; }
      else if (!clusterModeActive.value && isClustererOnMap) { map.geoObjects.remove(clusterer); isClustererOnMap = false; }
    }
  } catch (e) { }
  const itemsToProcess = [...markerStates];
  for (const item of itemsToProcess) {
    if (!item || !item.placemark) continue;
    try { map.geoObjects.remove(item.placemark); } catch (e) { }
    if (active.size === 0) { item.visible = false; } else { item.visible = active.has(categoryKeyForPoint(item.point)); }
    if (!item.visible) continue;
    if (editingState === item) {
      setPlacemarkDimmed(item.placemark, false);
      if (editPlacemark) { try { map.geoObjects.add(editPlacemark); } catch (e) { } }
      continue;
    }
    setPlacemarkDimmed(item.placemark, dimMapObjects || dimForEdit);
    try { if (!clusterModeActive.value) { map.geoObjects.add(item.placemark); } else if (clusterer) { clusterer.add(item.placemark); } } catch (e) { }
  }
  try { drawZones(); } catch (e) { }
}

function clearRoadEventObjects() {
  if (!map) return;
  try { if (clusterer) clusterer.removeAll(); } catch (e) { }
  try {
    if (clusterer && isClustererOnMap) {
      map.geoObjects.remove(clusterer);
      isClustererOnMap = false;
    }
  } catch (e) { }
  for (const item of markerStates) {
    try { if (item?.placemark) map.geoObjects.remove(item.placemark); } catch (e) { }
  }
  try { if (zoneCollection) zoneCollection.removeAll(); } catch (e) { }
}

let _zoomInterval = null;
function _doZoom(d) { if (map) map.setZoom(Math.min(Math.max(map.getZoom() + d, 0), 19), { smooth: true, duration: 200 }); }
function startZoom(d) { _doZoom(d); _zoomInterval = setInterval(() => _doZoom(d), 220); }
function stopZoom() { clearInterval(_zoomInterval); _zoomInterval = null; }

function getMapBbox(p = 0.2) {
  if (!map) return null;
  const [[minLat, minLon], [maxLat, maxLon]] = map.getBounds() || [];
  const latPad = (maxLat - minLat) * p, lonPad = (maxLon - minLon) * p;
  return { minLon: minLon - lonPad, minLat: minLat - latPad, maxLon: maxLon + lonPad, maxLat: maxLat + latPad };
}

function needsReload(bbox) {
  if (!lastLoadedBbox) return true;
  return bbox.minLon < lastLoadedBbox.minLon || bbox.minLat < lastLoadedBbox.minLat || bbox.maxLon > lastLoadedBbox.maxLon || bbox.maxLat > lastLoadedBbox.maxLat;
}

function bboxContains(outer, inner) {
  return outer.minLon <= inner.minLon
    && outer.minLat <= inner.minLat
    && outer.maxLon >= inner.maxLon
    && outer.maxLat >= inner.maxLat;
}

function isBboxCached(bbox) {
  return loadedEventBboxes.some(loadedBbox => bboxContains(loadedBbox, bbox));
}

function pointInsideBbox(point, bbox) {
  const coords = point?.location?.coordinates;
  if (!Array.isArray(coords) || coords.length < 2) return false;
  const lon = Number(coords[0]);
  const lat = Number(coords[1]);
  return Number.isFinite(lon)
    && Number.isFinite(lat)
    && lon >= bbox.minLon
    && lon <= bbox.maxLon
    && lat >= bbox.minLat
    && lat <= bbox.maxLat;
}

function getCachedPointsForBbox(bbox) {
  return Array.from(cachedEventPoints.values()).filter(point => pointInsideBbox(point, bbox));
}

function rememberCachedPoint(point) {
  if (point?.id === undefined || point?.id === null) return;
  cachedEventPoints.set(String(point.id), { ...point });
}

function rememberLoadedArea(bbox, points) {
  loadedEventBboxes.push({ ...bbox });
  if (loadedEventBboxes.length > EVENT_CACHE_MAX_AREAS) loadedEventBboxes.shift();
  for (const point of points) rememberCachedPoint(point);
  lastLoadedBbox = bbox;
}

function invalidateEventCache() {
  lastLoadedBbox = null;
  loadedEventBboxes = [];
  cachedEventPoints.clear();
}

async function loadPointsByBbox() {
  if (!map) return;
  currentZoom.value = map.getZoom();
  if (!shouldShowRoadEvents.value || map.getZoom() < LOAD_MIN_ZOOM) {
    clearRoadEventObjects();
    return;
  }
  const bbox = getMapBbox(0.2);
  if (!bbox) return;
  if (isBboxCached(bbox)) {
    applyNewPoints(getCachedPointsForBbox(bbox));
    statusText.value = `Точек: ${markerStates.length}`;
    return;
  }
  if (!needsReload(bbox)) return;
  isBboxLoading.value = true;
  try {
    const bboxStr = `${bbox.minLon},${bbox.minLat},${bbox.maxLon},${bbox.maxLat}`;
    let offset = 0, loaded = [];
    while (true) {
      const { data } = await axios.get("/api/events/events/", { params: { bbox: bboxStr, limit: 5000, offset } });
      const rows = Array.isArray(data?.results) ? data.results : [];
      loaded.push(...rows); offset += rows.length;
      if (!rows.length || offset >= (data?.count ?? 0)) break;
    }
    rememberLoadedArea(bbox, loaded);
    applyNewPoints(getCachedPointsForBbox(bbox));
    statusText.value = `Точек: ${markerStates.length}`;
  } catch (e) { console.error("Ошибка загрузки точек:", e); }
  finally { isBboxLoading.value = false; }
}

function applyNewPoints(points) {
  if (!map) return;
  if (!shouldShowRoadEvents.value) {
    clearRoadEventObjects();
    return;
  }
  const newIds = new Set(points.map(p => String(p.id)));
  const editingState = selectedPointState.value;
  markerStates.filter(item => !newIds.has(String(item.point.id)) && item !== editingState).forEach(item => {
    try { if (clusterer) clusterer.remove(item.placemark); map.geoObjects.remove(item.placemark); } catch (e) { }
    markerStatesMap.delete(String(item.point.id));
  });
  markerStates = markerStates.filter(item => newIds.has(String(item.point.id)) || item === editingState);
  const toAdd = [];
  for (const point of points) {
    const key = String(point.id);
    const existing = markerStatesMap.get(key);
    if (existing) {
      if (existing !== editingState) {
        Object.assign(existing.point, point);
        const [lon, lat] = point.location.coordinates;
        existing.lat = Number(lat); existing.lon = Number(lon);
        try { existing.placemark.geometry.setCoordinates([existing.lat, existing.lon]); const icon = getCategoryIconByItemId(point.class_item) || defaultEventIcon; updatePlacemarkMeta(existing.placemark, point, icon); } catch (e) { }
      }
    } else {
      const [lon, lat] = point.location.coordinates;
      const icon = getCategoryIconByItemId(point.class_item) || defaultEventIcon;
      const placemark = createPlacemark(point, Number(lat), Number(lon), icon);
      const state = { point, placemark, lat: Number(lat), lon: Number(lon), visible: true };
      placemark.events.add("click", () => openPointModal(state));
      markerStates.push(state); markerStatesMap.set(key, state); toAdd.push(placemark);
    }
  }
  ensureFilterState();
  if (toAdd.length) {
    const active = new Set(appliedCategoryFilters.value);
    markerStates.forEach(s => { if (toAdd.includes(s.placemark)) { if (active.size === 0) s.visible = false; else s.visible = active.has(categoryKeyForPoint(s.point)); } });
    const visibleNew = toAdd.filter(pm => markerStates.find(s => s.placemark === pm)?.visible);
    if (visibleNew.length) {
      try {
        if (clusterModeActive.value && clusterer) {
          if (!isClustererOnMap) { map.geoObjects.add(clusterer); isClustererOnMap = true; }
          clusterer.add(visibleNew);
        } else {
          visibleNew.forEach(pm => map.geoObjects.add(pm));
        }
      } catch (e) { }
    }
  }
  drawZones();
}

watch(() => [editForm.value.direction, editForm.value.speed_limit, editForm.value.angle, editForm.value.distance, editForm.value.dir_type], () => {
  if (!isEditMode.value || !selectedPointState.value || showMoveMarkerPanel.value) return;
  const p = selectedPointState.value.point;
  p.direction = Number(editForm.value.direction); p.speed_limit = Number(editForm.value.speed_limit);
  p.angle = Number(editForm.value.angle); p.distance = Number(editForm.value.distance);
  p.dir_type = Number(editForm.value.dir_type) === 2 ? 2 : 1;
  if (editZoneHandles.length) {
    updateZoneHandlePositions(editZoneHandles, editForm.value.lat, editForm.value.lon, Number(editForm.value.direction), Number(editForm.value.angle), Number(editForm.value.distance));
    updateZonePolygon(editZonePolygon, editForm.value.lat, editForm.value.lon, Number(editForm.value.direction), Number(editForm.value.angle), Number(editForm.value.distance), editForm.value.dir_type);
  }
  drawZones();
});

watch(() => editForm.value.class_item, (newItemId) => {
  if (!isEditMode.value || !selectedPointState.value) return;
  const icon = getCategoryIconByItemId(newItemId) || defaultEventIcon;
  if (editPlacemark) updatePlacemarkMeta(editPlacemark, { class_item: newItemId }, icon, true);
  drawZones();
});

watch(() => [addForm.value.direction, addForm.value.angle, addForm.value.distance, addForm.value.dir_type], () => {
  if (showAddPanel.value && addStep.value === 4) {
    if (addZonePolygon) {
      updateZonePolygon(addZonePolygon, addForm.value.lat, addForm.value.lon, Number(addForm.value.direction), Number(addForm.value.angle), Number(addForm.value.distance), addForm.value.dir_type);
      updateZoneHandlePositions(addZoneHandles, addForm.value.lat, addForm.value.lon, Number(addForm.value.direction), Number(addForm.value.angle), Number(addForm.value.distance));
    }
  }
});

async function initMap() {
  ymapsRef = await loadYandexMaps();
  await loadEventCatalog();
  map = new ymapsRef.Map(mapContainer.value, { center: INITIAL_CENTER, zoom: INITIAL_ZOOM, controls: [] });
  currentZoom.value = map.getZoom();
  createClusterer();
  zoneCollection = new ymapsRef.GeoObjectCollection(); map.geoObjects.add(zoneCollection);
  ensureFilterState(); await loadPointsByBbox();
  map.events.add("click", e => {
    const coords = e.get("coords");
    if (!coords) return;
    if (showAddPanel.value && addStep.value === 1) { setAddPoint(coords[0], coords[1]); }
    else if (isEditMode.value && showMoveMarkerPanel.value) { setEditPoint(coords[0], coords[1]); }
  });
  map.events.add("boundschange", () => {
    clearTimeout(clusterUpdateTimer); clearTimeout(bboxLoadTimer);
    clusterUpdateTimer = setTimeout(() => {
      const z = map.getZoom(); currentZoom.value = z;
      if (clusterModeActive.value && clusterer) clusterer.options.set("gridSize", calcClusterGridSizeByZoom(z));
      if (shouldShowRoadEvents.value) rebuildVisibleObjects();
      else clearRoadEventObjects();
    }, 90);
    bboxLoadTimer = setTimeout(() => loadPointsByBbox(), 600);
  });
}

onMounted(async () => {
  loadCurrentWeather();
  try { await initMap(); } catch (e) { console.error("Ошибка карты:", e); }
  finally { isLoading.value = false; }
});

onUnmounted(() => {
  clearTimeout(clusterUpdateTimer); clearTimeout(bboxLoadTimer);
  clearInterval(trafficUpdateInterval);
  if (trafficProvider) trafficProvider.setMap(null);
  mapContainer.value?.removeEventListener('wheel', onMapWheel);
  clearAddZone(); clearEditZone();
  if (editPlacemark && map) map.geoObjects.remove(editPlacemark);
  if (addPlacemark && map) map.geoObjects.remove(addPlacemark);
  if (searchPlacemark && map) map.geoObjects.remove(searchPlacemark);
  if (myLocationPlacemark && map) map.geoObjects.remove(myLocationPlacemark);
  stopZoom();
  if (map) map.destroy();
});
</script>

<template>
  <div class="page-wrap">
    <div class="page-header mb-4">
      <div>
        <h2 class="page-title"><i class="bi bi-map me-2"></i>Карта дорожных событий</h2>
        <div class="page-subtitle">Просмотр и управление точками на карте</div>
      </div>
    </div>

    <div class="custom-card map-card">
      <div class="map-wrap">
        <div ref="mapContainer" class="map-box"></div>

        <div v-if="isLoading" class="map-overlay">
          <div class="loading-card">
            <div class="spinner-border text-primary" role="status"><span class="visually-hidden">Загрузка...</span>
            </div>
            <div class="mt-2 text-dark fw-semibold">Загрузка данных...</div>
          </div>
        </div>

        <div v-if="!isLoading && isBboxLoading" class="bbox-loading-indicator">
          <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
          <span class="ms-2 small">Загрузка точек...</span>
        </div>

        <div v-if="showZoomMessage" class="zoom-bottom-message">
          Приблизьте, чтобы увидеть дорожные события
        </div>

        <div class="weather-widget" @click.stop="showWeatherDetails = !showWeatherDetails">
          <button class="weather-pill" type="button" title="Текущая погода">
            <span v-if="weatherLoading" class="spinner-border spinner-border-sm text-primary"></span>
            <span v-else class="weather-symbol">{{ weatherData ? getWeatherSymbol(weatherData.condition_code) : "?" }}</span>
            <span class="weather-temp">
              {{ weatherData ? formatTemp(weatherData.temperature) : "—" }}
            </span>
          </button>

          <transition name="filter-pop">
            <div v-if="showWeatherDetails" class="weather-details custom-card" @click.stop>
              <div class="weather-details-head">
                <div>
                  <div class="weather-details-title">Погода сейчас</div>
                  <div class="weather-details-place">
                    {{ weatherData?.location || "Текущее местоположение" }}
                    <span v-if="weatherData?.country">, {{ weatherData.country }}</span>
                  </div>
                </div>
                <button class="weather-refresh" type="button" :disabled="weatherLoading" @click.stop="loadCurrentWeather">
                  <i class="bi bi-arrow-clockwise"></i>
                </button>
              </div>

              <div v-if="weatherError" class="weather-error">
                {{ weatherError }}
              </div>

              <div v-else-if="weatherData" class="weather-grid">
                <div class="weather-main-row">
                  <span class="weather-big-symbol">{{ getWeatherSymbol(weatherData.condition_code) }}</span>
                  <div>
                    <div class="weather-big-temp">{{ formatTemp(weatherData.temperature) }}°</div>
                    <div class="weather-condition">{{ weatherData.condition || "Без описания" }}</div>
                  </div>
                </div>

                <div class="weather-detail-row">
                  <span>Ощущается</span>
                  <strong>{{ formatTemp(weatherData.feels_like) }}°</strong>
                </div>
                <div class="weather-detail-row">
                  <span>Влажность</span>
                  <strong>{{ weatherData.humidity ?? "—" }}%</strong>
                </div>
                <div class="weather-detail-row">
                  <span>Ветер</span>
                  <strong>{{ weatherData.wind_speed ?? "—" }} м/с</strong>
                </div>
                <div class="weather-detail-row">
                  <span>Облачность</span>
                  <strong>{{ weatherData.clouds ?? "—" }}%</strong>
                </div>

                <div v-if="weatherData.hourly?.length" class="weather-hourly">
                  <div class="weather-hourly-title">Почасовой прогноз</div>
                  <div class="weather-hourly-list">
                    <div v-for="hour in weatherData.hourly" :key="hour.time" class="weather-hour-card">
                      <div class="weather-hour-time">{{ formatWeatherHour(hour.time) }}</div>
                      <div class="weather-hour-symbol">{{ getWeatherSymbol(hour.condition_code) }}</div>
                      <div class="weather-hour-temp">{{ formatTemp(hour.temperature) }}°</div>
                      <div class="weather-hour-meta">
                        <span>{{ hour.precipitation_probability ?? "—" }}%</span>
                        <span>{{ hour.wind_speed ?? "—" }} м/с</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="weather-error">
                Разрешите доступ к геолокации, чтобы увидеть погоду.
              </div>
            </div>
          </transition>
        </div>

        <div class="map-search-widget" :class="{ open: showMapSearch }" @click.stop>
          <button class="map-search-toggle" type="button" title="Поиск по карте" @click="toggleMapSearch">
            <i class="bi bi-search"></i>
          </button>

          <transition name="map-search-pop">
            <div v-if="showMapSearch" class="map-search-panel">
              <div class="map-search-row">
                <i class="bi bi-search"></i>
                <input
                  v-model="mapSearchQuery"
                  class="map-search-input"
                  type="text"
                  placeholder="Найти город или место"
                  @keydown.enter.prevent="performMapSearch"
                />
                <button class="map-search-submit" type="button" :disabled="mapSearchBusy" @click="performMapSearch">
                  <span v-if="mapSearchBusy" class="spinner-border spinner-border-sm"></span>
                  <i v-else class="bi bi-arrow-right"></i>
                </button>
              </div>

              <div v-if="mapSearchError" class="map-search-error">{{ mapSearchError }}</div>
              <div v-if="mapSearchResults.length" class="map-search-results">
                <button
                  v-for="result in mapSearchResults"
                  :key="`${result.title}-${result.coords?.join(',')}`"
                  class="map-search-result"
                  type="button"
                  @click="selectMapSearchResult(result)"
                >
                  <span class="map-search-result-title">{{ result.title }}</span>
                  <span class="map-search-result-subtitle">{{ result.subtitle }}</span>
                </button>
              </div>
            </div>
          </transition>
        </div>

        <div class="map-controls-top-right">
          <button class="map-control-btn traffic-btn" type="button" @click="toggleTraffic" title="Пробки">
            <div class="traffic-btn-content">
              <div v-if="!trafficShown" class="traffic-circle traffic-off"><i
                  class="bi bi-car-front-fill traffic-car-icon"></i></div>
              <div v-else class="traffic-circle" :class="getTrafficClass(trafficLevel)"><span class="traffic-number">{{
                  trafficLevel }}</span></div>
            </div>
          </button>
          <button class="map-control-btn" type="button" @click="toggleFilterPanel" title="Фильтры"><i
              class="bi bi-funnel-fill"></i></button>
        </div>

        <div class="zoom-controls">
          <button class="zoom-btn" type="button" title="Приблизить" @mousedown.prevent="startZoom(1)"
            @mouseup="stopZoom" @mouseleave="stopZoom" @touchstart.prevent="startZoom(1)" @touchend="stopZoom"><i
              class="bi bi-plus-lg"></i></button>
          <button class="zoom-btn" type="button" title="Отдалить" @mousedown.prevent="startZoom(-1)" @mouseup="stopZoom"
            @mouseleave="stopZoom" @touchstart.prevent="startZoom(-1)" @touchend="stopZoom"><i
              class="bi bi-dash-lg"></i></button>
          <button class="zoom-btn location-btn" type="button" title="Моя геопозиция" :disabled="myLocationLoading"
            @click="focusMyLocation">
            <span v-if="myLocationLoading" class="spinner-border spinner-border-sm"></span>
            <img v-else :src="locationIcon" class="location-icon" alt="" />
          </button>
        </div>

        <div class="map-controls-bottom-right">
          <button class="add-event-btn" type="button" @click="openAddPanel" title="Добавить событие">
            <img :src="defaultEventIcon" class="add-event-icon" alt="" />
            <span class="add-event-plus">+</span>
            <span class="add-event-text">Добавить</span>
          </button>
        </div>

        <transition name="filter-pop">
          <div v-if="showFilterPanel" class="filter-panel custom-card p-3" @click.stop>
            <div class="card-title-custom mb-3"><i class="bi bi-funnel-fill me-2"></i>Фильтры</div>

            <div class="filter-cluster-toggle mb-3" @click="toggleClusterMode">
              <div class="d-flex align-items-center gap-2"><i class="bi bi-diagram-3 filter-cluster-icon"></i><span
                  class="fw-semibold">Кластеризация</span></div>
              <div class="filter-check" :class="{ active: clusterModeActive }"><i v-if="clusterModeActive"
                  class="bi bi-check-lg"></i></div>
            </div>

            <div class="filter-divider mb-3"></div>

            <div class="filter-quick-actions mb-3">
              <div class="d-flex gap-2">
                <button class="filter-action-btn filter-action-btn-off flex-fill" @click="disableAllFilters"><i
                    class="bi bi-eye-slash me-1"></i>Выключить всё</button>
                <button class="filter-action-btn filter-action-btn-on flex-fill" @click="enableAllFilters"><i
                    class="bi bi-eye me-1"></i>Включить всё</button>
              </div>
            </div>

            <div class="filter-divider mb-3"></div>

            <div class="filter-accordion">
              <div v-for="cls in catalogClasses" :key="cls.id" class="filter-accordion-item">
                <div class="filter-accordion-header" @click="toggleFilterClass(cls.id)">
                  <div class="d-flex align-items-center gap-2">
                    <div class="filter-class-checkbox" @click.stop="toggleDraftClass(cls.items)"
                      :class="{ 'active': isClassFullySelected(cls.items), 'partial': isClassPartiallySelected(cls.items) }">
                      <i v-if="isClassFullySelected(cls.items)" class="bi bi-check-lg"></i>
                      <i v-else-if="isClassPartiallySelected(cls.items)" class="bi bi-dash-lg"></i>
                    </div>
                    <img v-if="cls.icon" :src="resolveMediaUrl(cls.icon)" class="filter-class-icon" alt="" />
                    <i v-else class="bi bi-folder-fill filter-class-icon-placeholder"></i>
                    <span class="fw-semibold">{{ cls.name }}</span>
                    <span class="badge bg-primary rounded-pill ms-1" style="font-size:11px;">{{ cls.items?.length || 0
                      }}</span>
                  </div>
                  <i class="bi" :class="expandedFilterClasses[cls.id] ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
                </div>
                <div v-if="expandedFilterClasses[cls.id]" class="filter-accordion-body">
                  <div v-if="!cls.items?.length" class="text-muted small p-2">Нет элементов</div>
                  <div v-else class="filter-items-list">
                    <div v-for="item in cls.items" :key="item.id" class="filter-item"
                      @click="toggleDraftCategory(`cat:${item.id}`)">
                      <div class="d-flex align-items-center gap-2">
                        <img v-if="item.icon" :src="resolveMediaUrl(item.icon)" class="filter-item-icon" alt="" />
                        <img v-else-if="cls.icon" :src="resolveMediaUrl(cls.icon)" class="filter-item-icon" alt="" />
                        <i v-else class="bi bi-tag-fill filter-item-icon-placeholder"></i>
                        <span class="filter-label">{{ item.name }}</span>
                      </div>
                      <div class="filter-check" :class="{ active: draftCategoryFilters.includes(`cat:${item.id}`) }"><i
                          v-if="draftCategoryFilters.includes(`cat:${item.id}`)" class="bi bi-check-lg"></i></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="filter-actions d-flex gap-2 mt-3">
              <button class="btn-cancel flex-fill" @click="resetCategoryFilters">Сбросить</button>
              <button class="btn-save flex-fill" @click="applyCategoryFilters">Применить</button>
            </div>
          </div>
        </transition>

        <transition name="add-pop">
          <div v-if="showAddPanel" class="event-floating-panel add-floating-panel" @click.stop>
            <div class="event-modal-card add-flow-card" @click.stop>
              <div class="event-modal-header add-flow-header">
                <h5 class="mb-0">{{ addStep === 1 ? "Укажите точку на карте" : "Выберите событие" }}</h5>
                <button class="close-btn" @click.stop="closeAddPanel">×</button>
              </div>
              <div class="event-modal-body">
                <template v-if="addStep === 1">
                  <div class="add-step1-wrap">
                    <div class="add-step1-grid">
                      <div class="add-step1-field"><label class="add-step1-label">Широта</label><input
                          :value="addForm.lat" class="add-step1-input" disabled /></div>
                      <div class="add-step1-field"><label class="add-step1-label">Долгота</label><input
                          :value="addForm.lon" class="add-step1-input" disabled /></div>
                    </div>
                    <div class="add-hint">Кликните по карте, чтобы выбрать точку</div>
                  </div>
                </template>
                <template v-else-if="addStep === 2">
                  <div class="category-grid">
                    <button v-for="eventClass in pagedEventClasses" :key="eventClass.id" class="category-grid-item"
                      type="button" @click="selectEventClass(eventClass)">
                      <img :src="getEventClassIcon(eventClass)" class="category-grid-icon" alt="" />
                      <span class="category-grid-label">{{ eventClass.name }}</span>
                    </button>
                  </div>
                </template>
                <template v-else-if="addStep === 3">
                  <div class="detail-carousel-wrap">
                    <button class="add-nav-btn add-nav-btn-left" :disabled="!canItemPrev"
                      @click="addItemPage -= 1">‹</button>
                    <div class="detail-options-grid">
                      <button v-for="item in pagedClassItems" :key="item.id" class="detail-option-btn" type="button"
                        @click="selectEventClassItem(item)">
                        <img :src="getClassItemIcon(item)" class="detail-item-icon" alt="" />
                        <span class="detail-label">{{ item.name }}</span>
                      </button>
                    </div>
                    <button class="add-nav-btn add-nav-btn-right" :disabled="!canItemNext"
                      @click="addItemPage += 1">›</button>
                  </div>
                </template>
                <template v-else>
                  <div class="add-hint mb-3"><i class="bi bi-info-circle me-2"></i>Тяните за синие круги для угла, за
                    оранжевый — для дистанции и азимута</div>
                  <div class="add-params-grid">
                    <div class="add-param-item"><label class="add-param-label">Азимут</label>
                      <div class="add-param-value">{{ addForm.direction }}°</div><input
                        v-model.number="addForm.direction" type="range" min="0" max="360" step="5"
                        class="add-param-range" />
                    </div>
                    <div class="add-param-item"><label class="add-param-label">Угол</label>
                      <div class="add-param-value">{{ addForm.angle }}°</div><input v-model.number="addForm.angle"
                        type="range" min="5" max="180" step="5" class="add-param-range" />
                    </div>
                    <div class="add-param-item"><label class="add-param-label">Дистанция</label>
                      <div class="add-param-value">{{ addForm.distance }} м</div><input
                        v-model.number="addForm.distance" type="range" min="50" max="2000" step="10"
                        class="add-param-range" />
                    </div>
                    <div class="add-param-item"><label class="add-param-label">Скорость</label>
                      <div class="add-param-value">{{ addForm.speed_limit }} км/ч</div><input
                        v-model.number="addForm.speed_limit" type="range" min="0" max="200" step="5"
                        class="add-param-range" />
                    </div>
                    <div class="add-param-item">
                      <label class="add-param-label">Направление</label>
                      <div class="form-check form-switch ms-2">
                        <input id="addDirTypeSwitch" class="form-check-input" type="checkbox"
                          :checked="addForm.dir_type === 2"
                          @change="addForm.dir_type = $event.target.checked ? 2 : 1" />
                        <label class="form-check-label" for="addDirTypeSwitch"
                          style="font-size:14px;font-weight:600;">{{ addForm.dir_type === 2 ? "В обе стороны" : "В одну сторону" }}</label>
                      </div>
                    </div>
                    <div class="add-param-item add-param-full"><label class="add-param-label">Описание</label><input
                        v-model="addForm.details" class="form-control form-control-sm" placeholder="Описание события" />
                    </div>
                  </div>
                </template>
                <div v-if="addError" class="alert alert-danger py-2 px-3 mt-3 mb-0">{{ addError }}</div>
              </div>
              <div class="event-modal-actions">
                <template v-if="addStep === 1">
                  <button class="btn add-step1-btn add-step1-btn-primary" @click.stop="goAddStep2">Продолжить</button>
                  <button class="btn add-step1-btn add-step1-btn-secondary"
                    @click.stop="closeAddPanel">Отменить</button>
                </template>
                <template v-else-if="addStep === 2"><button class="btn add-step1-btn add-step1-btn-secondary"
                    @click.stop="addStep = 1">Назад</button></template>
                <template v-else-if="addStep === 3"><button class="btn add-step1-btn add-step1-btn-secondary"
                    @click.stop="addStep = 2">Назад</button></template>
                <template v-else>
                  <button class="btn add-step1-btn add-step1-btn-secondary" :disabled="addBusy"
                    @click.stop="addStep = 3">Назад</button>
                  <button class="btn add-step1-btn add-step1-btn-primary" :disabled="addBusy"
                    @click.stop="createPoint">Добавить</button>
                </template>
              </div>
            </div>
          </div>
        </transition>

        <transition name="add-pop">
          <div v-if="showPointModal && !showMoveMarkerPanel" class="event-floating-panel add-floating-panel"
            @click.stop>
            <div class="event-modal-card add-flow-card" :class="{ 'event-view-card': !isEditMode }" @click.stop>
              <div class="event-modal-header add-flow-header" :class="{ 'event-view-header': !isEditMode }">
                <h5 class="mb-0">
                  <template v-if="isEditMode">Редактирование события</template>
                  <template v-else>
                    <span class="event-title-icon">
                      <img v-if="currentCategoryIcon" :src="currentCategoryIcon" alt="" />
                      <i v-else class="bi bi-camera-fill"></i>
                    </span>
                    <span>{{ getSelectedEventTitle() }}</span>
                  </template>
                </h5>
                <button class="close-btn" @click.stop="closePointModal">×</button>
              </div>
              <div class="event-modal-body">
                <template v-if="!isEditMode">
                  <div class="event-view-layout">
                    <div class="event-view-main">
                      <div class="event-view-description">{{ getSelectedEventDetails() }}</div>
                      <div class="event-view-meta">{{ getSelectedEventMeta() }}</div>

                      <div class="event-vote-row">
                        <button class="event-vote-btn event-vote-confirm" :disabled="voteBusy" @click.stop="voteForEvent(1)">
                          <span>{{ editForm.confirmations }}</span>
                          <i class="bi bi-hand-thumbs-up-fill"></i>
                        </button>
                        <span class="event-vote-time">{{ formatRelativeTime(selectedPointState?.point?.last_seen_at) }}</span>

                        <button class="event-vote-btn event-vote-deny" :disabled="voteBusy" @click.stop="voteForEvent(-1)">
                          <span>{{ editForm.denials }}</span>
                          <i class="bi bi-hand-thumbs-down-fill"></i>
                        </button>
                        <span class="event-vote-time">{{ formatRelativeTime(selectedPointState?.point?.created_at) }}</span>
                      </div>
                    </div>

                    <div class="event-photo-side">
                      <input ref="photoInput" class="d-none" type="file" accept="image/*" @change="onMediaFilePicked" />
                      <button class="event-photo-btn" :disabled="modalBusy" @click.stop="photoInput?.click()">
                        <i class="bi bi-camera-fill"></i>
                        <span class="event-photo-plus"><i class="bi bi-plus"></i></span>
                      </button>
                      <div class="event-photo-title">Фото</div>
                      <div v-if="eventMedia.length" class="event-photo-count">{{ eventMedia.length }}</div>
                    </div>
                  </div>

                  <div class="event-params-strip">
                    <span class="event-param-chip"><i class="bi bi-compass-fill"></i> Азимут: {{ editForm.direction }}°</span>
                    <span class="event-param-chip"><i class="bi bi-rulers"></i> Угол: {{ editForm.angle }}°</span>
                    <span class="event-param-chip"><i class="bi bi-signpost-split-fill"></i> Дистанция: {{ editForm.distance }} м</span>
                    <span class="event-param-chip"><i class="bi bi-sign-turn-right-fill"></i> Направление: {{ editForm.dir_type === 2 ? "В обе стороны" : "В одну сторону" }}</span>
                  </div>

                  <div v-if="eventMedia.length" class="event-view-media-row">
                    <div v-for="m in eventMedia.slice(0, 4)" :key="m.id" class="media-thumb-wrap event-view-thumb">
                      <img :src="m.image_url || resolveMediaUrl(m.image)" class="media-thumb" alt="" />
                      <button class="btn btn-sm btn-danger media-del-btn" @click.stop="deleteEventMedia(m.id)">×</button>
                    </div>
                  </div>

                  <div class="event-view-footer">
                    <div class="event-reliability" :class="getEventReliabilityClass()">
                      <span class="event-reliability-icon"><i class="bi bi-shield-check"></i></span>
                      <span>{{ getEventReliabilityLabel() }}</span>
                    </div>

                    <div class="event-view-actions">
                      <button class="event-action-btn event-edit-btn" @click.stop="toggleEditMode(true)">
                        <i class="bi bi-pencil-square"></i>
                        <span>Редак.</span>
                      </button>
                      <button class="event-action-btn event-archive-btn" :disabled="modalBusy" @click.stop="archivePoint">
                        <i class="bi bi-archive-fill"></i>
                        <span>Архив.</span>
                      </button>
                    </div>
                  </div>

                  <div v-if="modalError" class="alert alert-danger py-2 px-3 mt-3 mb-0">{{ modalError }}</div>
                  <div v-if="modalSuccess" class="alert alert-success py-2 px-3 mt-3 mb-0"><i
                      class="bi bi-check-circle me-2"></i>{{ modalSuccess }}</div>
                </template>
                <template v-else>
                  <div class="mb-3">
                    <label class="add-param-label mb-2">Категория события</label>
                    <div class="edit-category-dropdown-wrapper">
                      <button class="edit-category-trigger"
                        @click.stop="showEditCategoryDropdown = !showEditCategoryDropdown">
                        <div class="d-flex align-items-center gap-2">
                          <img v-if="currentCategoryIcon" :src="currentCategoryIcon" class="filter-item-icon" alt="" />
                          <i v-else class="bi bi-tag-fill filter-item-icon-placeholder"></i>
                          <span>{{ currentCategoryName }}</span>
                        </div>
                        <i class="bi bi-chevron-down"></i>
                    </button>
                      <div v-if="showEditCategoryDropdown" class="edit-category-menu" @click.stop>
                        <div v-for="cls in catalogClasses" :key="cls.id">
                          <div class="edit-category-class-header"
                            @click.stop="expandedEditClasses[cls.id] = !expandedEditClasses[cls.id]">
                            <div class="d-flex align-items-center gap-2">
                              <img v-if="cls.icon" :src="resolveMediaUrl(cls.icon)" class="filter-item-icon" alt="" />
                              <i v-else class="bi bi-folder-fill filter-item-icon-placeholder"></i>
                              <span class="fw-semibold">{{ cls.name }}</span>
                            </div>
                            <i class="bi"
                              :class="expandedEditClasses[cls.id] ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
                          </div>
                          <div v-if="expandedEditClasses[cls.id] && cls.items?.length" class="edit-category-items">
                            <div v-for="item in cls.items" :key="item.id" class="edit-category-item"
                              :class="{ active: editForm.class_item === item.id }"
                              @click.stop="selectEditCategory(item.id)">
                              <img v-if="item.icon" :src="resolveMediaUrl(item.icon)" class="filter-item-icon" alt="" />
                              <img v-else-if="cls.icon" :src="resolveMediaUrl(cls.icon)" class="filter-item-icon"
                                alt="" />
                              <i v-else class="bi bi-tag-fill filter-item-icon-placeholder"></i>
                              <span>{{ item.name }}</span>
                              <i v-if="editForm.class_item === item.id" class="bi bi-check-lg ms-auto text-primary"></i>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="mb-3">
                    <button class="btn add-step1-btn add-step1-btn-primary w-100" @click.stop="startMovingMarker">
                      <i class="bi bi-geo-alt me-2"></i>Переместить метку
                    </button>
                  </div>

                  <div class="add-params-grid">
                    <div class="add-param-item"><label class="add-param-label">Азимут</label>
                      <div class="add-param-value">{{ editForm.direction }}°</div><input
                        v-model.number="editForm.direction" type="range" min="0" max="360" step="5"
                        class="add-param-range" />
                    </div>
                    <div class="add-param-item"><label class="add-param-label">Угол</label>
                      <div class="add-param-value">{{ editForm.angle }}°</div><input v-model.number="editForm.angle"
                        type="range" min="5" max="180" step="5" class="add-param-range" />
                    </div>
                    <div class="add-param-item"><label class="add-param-label">Дистанция</label>
                      <div class="add-param-value">{{ editForm.distance }} м</div><input
                        v-model.number="editForm.distance" type="range" min="50" max="2000" step="10"
                        class="add-param-range" />
                    </div>
                    <div class="add-param-item"><label class="add-param-label">Скорость</label>
                      <div class="add-param-value">{{ editForm.speed_limit }} км/ч</div><input
                        v-model.number="editForm.speed_limit" type="range" min="0" max="200" step="5"
                        class="add-param-range" />
                    </div>
                    <div class="add-param-item">
                      <label class="add-param-label">Направление</label>
                      <div class="form-check form-switch ms-2">
                        <input id="editDirTypeSwitch" class="form-check-input" type="checkbox"
                          :checked="editForm.dir_type === 2"
                          @change="editForm.dir_type = $event.target.checked ? 2 : 1" />
                        <label class="form-check-label" for="editDirTypeSwitch"
                          style="font-size:14px;font-weight:600;">{{ editForm.dir_type === 2 ? "В обе стороны" : "В одну сторону" }}</label>
                      </div>
                    </div>
                  </div>
                  <div v-if="modalError" class="alert alert-danger py-2 px-3 mt-3 mb-0">{{ modalError }}</div>
                  <div v-if="modalSuccess" class="alert alert-success py-2 px-3 mt-3 mb-0"><i
                      class="bi bi-check-circle me-2"></i>{{ modalSuccess }}</div>
                </template>
              </div>
              <div v-if="isEditMode" class="event-modal-actions">
                <button class="btn add-step1-btn add-step1-btn-secondary" :disabled="modalBusy"
                  @click.stop="toggleEditMode(false)">Отмена</button>
                <button class="btn add-step1-btn add-step1-btn-primary" :disabled="modalBusy"
                  @click.stop="savePoint">Сохранить</button>
              </div>
            </div>
          </div>
        </transition>

        <transition name="add-pop">
          <div v-if="showPointModal && showMoveMarkerPanel" class="event-floating-panel add-floating-panel" @click.stop>
            <div class="event-modal-card add-flow-card" @click.stop>
              <div class="event-modal-header add-flow-header">
                <h5 class="mb-0">Укажите новую точку на карте</h5>
                <button class="close-btn" @click.stop="cancelMovingMarker">×</button>
              </div>
              <div class="event-modal-body">
                <div class="add-step1-wrap">
                  <div class="add-step1-grid">
                    <div class="add-step1-field"><label class="add-step1-label">Широта</label><input
                        :value="editForm.lat" class="add-step1-input" disabled /></div>
                    <div class="add-step1-field"><label class="add-step1-label">Долгота</label><input
                        :value="editForm.lon" class="add-step1-input" disabled /></div>
                  </div>
                  <div class="add-hint">Кликните по карте, чтобы выбрать новую точку</div>
                </div>
              </div>
              <div class="event-modal-actions">
                <button class="btn add-step1-btn add-step1-btn-primary"
                  @click.stop="confirmMovingMarker">Продолжить</button>
                <button class="btn add-step1-btn add-step1-btn-secondary"
                  @click.stop="cancelMovingMarker">Отмена</button>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <div v-if="statusText" class="status-badge mt-3"><i class="bi bi-database me-2"></i>{{ statusText }}</div>
  </div>
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
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.card-title-custom {
  font-size: 18px;
  font-weight: 800;
  margin-bottom: 18px;
  color: #111;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  background: rgba(13, 110, 253, 0.1);
  color: #0d6efd;
  padding: 8px 16px;
  border-radius: 14px;
  font-weight: 600;
  font-size: 14px;
}

.map-card {
  padding: 0;
  overflow: hidden;
  height: calc(100vh - 140px);
  min-height: 600px;
}

.map-wrap {
  position: relative;
  width: 100%;
  height: 100%;
}

.map-box {
  width: 100%;
  height: 100%;
  min-height: 600px;
  border-radius: 24px;
  overflow: hidden;
}

.map-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(4px);
  border-radius: 24px;
  z-index: 15;
  pointer-events: none;
}

.loading-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px 32px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.zoom-bottom-message {
  position: absolute;
  left: 50%;
  bottom: 86px;
  z-index: 24;
  max-width: calc(100% - 48px);
  transform: translateX(-50%);
  padding: 10px 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.9);
  color: #080808;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(10px);
  font-size: 15px;
  font-weight: 500;
  line-height: 1.15;
  text-align: center;
  white-space: nowrap;
  pointer-events: none;
}

.bbox-loading-indicator {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  top: 16px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20px;
  padding: 8px 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  z-index: 20;
  display: flex;
  align-items: center;
}

.weather-widget {
  position: absolute;
  left: 16px;
  top: 16px;
  z-index: 24;
}

.weather-pill {
  min-width: 76px;
  height: 42px;
  border: 0;
  border-radius: 22px;
  padding: 0 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(10px);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.weather-pill:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.23);
}

.weather-symbol {
  color: #2f86ff;
  font-size: 23px;
  line-height: 1;
  font-weight: 800;
}

.weather-temp {
  color: #333;
  font-size: 22px;
  line-height: 1;
  font-weight: 900;
}

.weather-details {
  position: absolute;
  left: 0;
  top: 52px;
  width: 370px;
  max-width: calc(100vw - 40px);
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 18px 46px rgba(15, 23, 42, 0.18);
}

.weather-details-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.weather-details-title {
  color: #111827;
  font-size: 17px;
  font-weight: 900;
}

.weather-details-place {
  color: #6b7280;
  font-size: 13px;
  font-weight: 700;
}

.weather-refresh {
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: #0d6efd;
  background: #eef4ff;
}

.weather-main-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
  padding: 14px;
  background: #f8fafc;
  border-radius: 18px;
}

.weather-big-symbol {
  color: #2f86ff;
  font-size: 42px;
  line-height: 1;
}

.weather-big-temp {
  color: #111827;
  font-size: 32px;
  font-weight: 900;
  line-height: 1;
}

.weather-condition {
  color: #6b7280;
  font-size: 14px;
  font-weight: 750;
  text-transform: capitalize;
}

.weather-detail-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 2px;
  color: #6b7280;
  font-size: 14px;
  font-weight: 750;
  border-bottom: 1px solid #edf1f6;
}

.weather-detail-row:last-child {
  border-bottom: 0;
}

.weather-detail-row strong {
  color: #111827;
  font-weight: 900;
}

.weather-hourly {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #edf1f6;
}

.weather-hourly-title {
  margin-bottom: 10px;
  color: #111827;
  font-size: 14px;
  font-weight: 900;
}

.weather-hourly-list {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 86px;
  gap: 9px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.weather-hour-card {
  padding: 10px 8px;
  text-align: center;
  background: #f8fafc;
  border: 1px solid #edf1f6;
  border-radius: 16px;
}

.weather-hour-time {
  color: #6b7280;
  font-size: 12px;
  font-weight: 850;
}

.weather-hour-symbol {
  margin: 5px 0 3px;
  color: #2f86ff;
  font-size: 23px;
  line-height: 1;
}

.weather-hour-temp {
  color: #111827;
  font-size: 18px;
  font-weight: 900;
}

.weather-hour-meta {
  display: grid;
  gap: 2px;
  margin-top: 5px;
  color: #6b7280;
  font-size: 11px;
  font-weight: 750;
}

.weather-error {
  padding: 12px;
  color: #b42318;
  background: #fff1f0;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 750;
}

.map-search-widget {
  position: absolute;
  left: 114px;
  top: 16px;
  z-index: 25;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.map-search-toggle {
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #4b5b5e;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(10px);
  font-size: 22px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.map-search-toggle:hover,
.map-search-widget.open .map-search-toggle {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.23);
}

.map-search-panel {
  width: 360px;
  max-width: calc(100vw - 170px);
  padding: 10px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.2);
  backdrop-filter: blur(12px);
}

.map-search-row {
  height: 42px;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) 34px;
  align-items: center;
  gap: 8px;
  padding: 0 6px 0 12px;
  background: #f8fafc;
  border: 1px solid #e5eaf2;
  border-radius: 16px;
  color: #6b7280;
}

.map-search-input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: #111827;
  font-size: 15px;
  font-weight: 750;
}

.map-search-input::placeholder {
  color: #8b95a5;
}

.map-search-submit {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #fff;
  background: #1677ff;
}

.map-search-submit:disabled {
  opacity: 0.65;
}

.map-search-error {
  margin-top: 8px;
  padding: 9px 11px;
  color: #b42318;
  background: #fff1f0;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 750;
}

.map-search-results {
  display: grid;
  gap: 6px;
  margin-top: 8px;
  max-height: 260px;
  overflow-y: auto;
}

.map-search-result {
  border: 0;
  display: grid;
  gap: 2px;
  padding: 10px 12px;
  text-align: left;
  background: #fff;
  border-radius: 14px;
  transition: background 0.18s ease, transform 0.18s ease;
}

.map-search-result:hover {
  background: #eef4ff;
  transform: translateX(2px);
}

.map-search-result-title {
  color: #111827;
  font-size: 14px;
  font-weight: 900;
}

.map-search-result-subtitle {
  color: #6b7280;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.map-search-pop-enter-active,
.map-search-pop-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease, max-width 0.24s ease;
  transform-origin: left center;
}

.map-search-pop-enter-from,
.map-search-pop-leave-to {
  opacity: 0;
  transform: translateX(-10px) scaleX(0.85);
}

.zoom-controls {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 20;
}

.zoom-btn {
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.95);
  color: #111;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transition: 0.2s ease;
  backdrop-filter: blur(8px);
}

.zoom-btn .bi-plus-lg,
.zoom-btn .bi-dash-lg {
  font-size: 22px;
  font-weight: 900;
  -webkit-text-stroke: 1.2px currentColor;
}

.zoom-btn:hover {
  background: #fff;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.18);
  transform: scale(1.05);
}

.zoom-btn:disabled {
  cursor: default;
  opacity: 0.75;
  transform: none;
}

.location-btn {
  color: #1677ff;
}

.location-icon {
  width: 22px;
  height: 22px;
  object-fit: contain;
  display: block;
}

.map-controls-top-right {
  position: absolute;
  right: 16px;
  top: 16px;
  display: flex;
  gap: 8px;
  z-index: 20;
}

.map-control-btn {
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.95);
  color: #111;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transition: 0.2s ease;
  backdrop-filter: blur(8px);
}

.map-control-btn:hover {
  background: #fff;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.18);
}

.traffic-btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.traffic-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s ease;
}

.traffic-circle.traffic-off {
  background: #9e9e9e;
}

.traffic-circle.traffic-green {
  background: #43a047;
}

.traffic-circle.traffic-yellow {
  background: #f2c94c;
}

.traffic-circle.traffic-red {
  background: #e53935;
}

.traffic-number {
  font-size: 15px;
  font-weight: 800;
  color: #fff;
  line-height: 1;
}

.traffic-car-icon {
  font-size: 16px;
  color: #fff;
}

.map-controls-bottom-right {
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 30;
}

.add-event-btn {
  height: 48px;
  padding: 0 20px 0 12px;
  border-radius: 24px;
  border: 0;
  background: #fff;
  color: #111;
  font-size: 15px;
  font-weight: 700;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.add-event-btn:hover {
  background: #f8f9fa;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.2);
  transform: translateY(-1px);
}

.add-event-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
  flex-shrink: 0;
}

.add-event-plus {
  font-size: 18px;
  color: #111;
  font-weight: 800;
  line-height: 1;
}

.add-event-text {
  font-size: 15px;
  font-weight: 700;
  color: #111;
}

.filter-panel {
  position: absolute;
  right: 16px;
  top: 72px;
  width: 320px;
  max-height: calc(100% - 100px);
  overflow-y: auto;
  z-index: 25;
  border-radius: 20px !important;
  padding: 16px;
}

.filter-cluster-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f8fafc;
  cursor: pointer;
  transition: 0.15s ease;
}

.filter-cluster-toggle:hover {
  background: #f0f4ff;
}

.filter-cluster-icon {
  font-size: 20px;
  color: #0d6efd;
}

.filter-check {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  border: 2px solid #0d6efd;
  background: #fff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: 0.2s ease;
  flex-shrink: 0;
}

.filter-check.active {
  background: #0d6efd;
  color: #fff;
}

.filter-action-btn {
  border: 0;
  border-radius: 12px;
  padding: 8px 12px;
  font-weight: 600;
  font-size: 11px;
  cursor: pointer;
  transition: 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.filter-action-btn-off {
  background: #eef1f4;
  color: #6c757d;
}

.filter-action-btn-off:hover {
  background: #dfe3e8;
  color: #111;
}

.filter-action-btn-on {
  background: #0d6efd;
  color: #fff;
}

.filter-action-btn-on:hover {
  background: #0b5ed7;
}

.filter-divider {
  height: 1px;
  background: #eef1f4;
}

.filter-accordion {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-accordion-item {
  border-radius: 12px;
  overflow: hidden;
}

.filter-accordion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  user-select: none;
  transition: 0.15s ease;
  border-radius: 12px;
}

.filter-accordion-header:hover {
  background: rgba(13, 110, 253, 0.04);
}

.filter-class-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
  border-radius: 6px;
}

.filter-class-icon-placeholder {
  font-size: 18px;
  color: #0d6efd;
}

.filter-accordion-body {
  padding: 4px 8px 8px;
}

.filter-items-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: 0.15s ease;
}

.filter-item:hover {
  background: rgba(13, 110, 253, 0.04);
}

.filter-item.active {
  background: rgba(13, 110, 253, 0.08);
  color: #0d6efd;
  font-weight: 600;
}

.filter-item-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
  border-radius: 4px;
}

.filter-item-icon-placeholder {
  font-size: 16px;
  color: #6f42c1;
}

.filter-label {
  font-size: 14px;
  font-weight: 500;
  color: #111;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.filter-quick-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-class-checkbox {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  border: 2px solid #0d6efd;
  background: #fff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: 0.2s ease;
  flex-shrink: 0;
  cursor: pointer;
}

.filter-class-checkbox.active {
  background: #0d6efd;
  color: #fff;
}

.filter-class-checkbox.partial {
  background: #0d6efd;
  color: #fff;
  opacity: 0.7;
}

.filter-class-checkbox:hover {
  border-color: #0b5ed7;
  background: rgba(13, 110, 253, 0.1);
}

.filter-class-checkbox.active:hover {
  background: #0b5ed7;
}

.btn-cancel,
.btn-save {
  border: 0;
  border-radius: 14px;
  padding: 10px 16px;
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

.btn-save:hover {
  background: #0b5ed7;
}

.event-floating-panel {
  position: absolute;
  z-index: 30;
  pointer-events: none;
}

.add-floating-panel {
  right: 16px;
  bottom: 84px;
}

.event-modal-card {
  width: min(440px, calc(100vw - 48px));
  background: #f8f9fa;
  border-radius: 20px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
  overflow: hidden;
  pointer-events: auto;
}

.event-view-card {
  width: min(420px, calc(100vw - 36px));
  padding: 10px;
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 14px 42px rgba(15, 23, 42, 0.15);
}

.event-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid #eef1f4;
  font-size: 16px;
  font-weight: 700;
}

.add-flow-header {
  margin: 8px 10px 0;
  border-bottom: none;
  border-radius: 14px;
  background: #fff;
  padding: 10px 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.event-view-header {
  min-height: 44px;
  margin: 0 0 10px;
  padding: 8px 10px 8px 14px;
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 7px 18px rgba(15, 23, 42, 0.12);
}

.event-view-header h5 {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  color: #050505;
  font-size: 22px;
  font-weight: 800;
  line-height: 1.05;
}

.event-title-icon {
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 0;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: #111;
  font-size: 18px;
}

.event-title-icon img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.event-view-header .close-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #fff;
  color: #333;
  font-size: 30px;
  font-weight: 500;
  box-shadow: 0 5px 16px rgba(15, 23, 42, 0.16);
}

.event-modal-body {
  padding: 16px 18px;
  max-height: 55vh;
  overflow-y: auto;
}

.event-view-card .event-modal-body {
  max-height: min(68vh, 430px);
  padding: 5px 10px 10px;
}

.event-view-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 118px;
  gap: 12px;
  align-items: start;
}

.event-view-description {
  color: #050505;
  font-size: 17px;
  font-weight: 500;
  line-height: 1.25;
}

.event-view-meta {
  margin-top: 8px;
  color: #9b9b9b;
  font-size: 13px;
  font-weight: 400;
}

.event-vote-row {
  display: grid;
  grid-template-columns: auto auto auto auto;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
}

.event-vote-btn {
  min-width: 45px;
  height: 24px;
  border: 0;
  border-radius: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #fff;
  font-size: 13px;
  font-weight: 800;
}

.event-vote-confirm {
  background: #278ff4;
}

.event-vote-deny {
  background: #9f9f9f;
}

.event-vote-time {
  color: #9b9b9b;
  font-size: 11px;
  font-weight: 400;
  white-space: nowrap;
}

.event-photo-side {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 5px 8px;
  padding-top: 3px;
}

.event-photo-btn {
  position: relative;
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #333;
  background: #fff;
  font-size: 18px;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.14);
}

.event-photo-plus {
  position: absolute;
  right: -3px;
  top: -5px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: #3b95ef;
  font-size: 13px;
}

.event-photo-title {
  color: #333;
  font-size: 13px;
  font-weight: 800;
}

.event-photo-count {
  grid-column: 2;
  color: #9b9b9b;
  font-size: 11px;
  font-weight: 500;
}

.event-params-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.event-param-chip {
  min-height: 22px;
  padding: 4px 8px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #a0a0a0;
  background: #fff;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.14);
  font-size: 10px;
  font-weight: 600;
}

.event-view-media-row {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}

.event-view-thumb {
  width: 48px;
  height: 38px;
}

.event-view-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 20px;
}

.event-reliability {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 800;
}

.event-reliability.high {
  color: #61d47a;
}

.event-reliability.medium {
  color: #f2b640;
}

.event-reliability.low {
  color: #ff4b55;
}

.event-reliability-icon {
  width: 34px;
  height: 34px;
  border: 2px solid currentColor;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 22px;
}

.event-view-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.event-action-btn {
  min-width: 76px;
  height: 36px;
  border: 0;
  border-radius: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 800;
  box-shadow: 0 7px 15px rgba(15, 23, 42, 0.14);
}

.event-edit-btn {
  color: #2388ed;
  background: #dbe8ff;
}

.event-archive-btn {
  color: #ff3038;
  background: #ffd7d7;
}

.event-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px 16px;
  border-top: 1px solid #eef1f4;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: 0;
  background: transparent;
  font-size: 24px;
  line-height: 1;
  color: #6c757d;
  cursor: pointer;
  border-radius: 8px;
  transition: 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: #f0f2f5;
  color: #111;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f2f5;
  font-size: 14px;
}

.info-row span {
  color: #6c757d;
}

.info-row strong {
  color: #111;
}

.add-step1-wrap {
  padding: 8px 0;
}

.add-step1-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.add-step1-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.add-step1-label {
  font-size: 15px;
  font-weight: 700;
  color: #111;
}

.add-step1-input {
  width: 100%;
  height: 40px;
  border: 1px solid #dfe3e8;
  border-radius: 12px;
  background: #fff;
  padding: 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: #111;
}

.add-hint {
  margin-top: 12px;
  font-size: 13px;
  color: #6c757d;
  text-align: center;
}

.add-step1-btn {
  min-width: 120px;
  height: 40px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 700;
  border: 0;
  cursor: pointer;
  transition: 0.15s ease;
}

.add-step1-btn-primary {
  background: #0d6efd;
  color: #fff;
}

.add-step1-btn-primary:hover {
  background: #0b5ed7;
}

.add-step1-btn-secondary {
  background: #eef1f4;
  color: #111;
}

.add-step1-btn-secondary:hover {
  background: #dfe3e8;
}

.add-step1-btn-danger {
  background: #dc3545;
  color: #fff;
}

.add-step1-btn-danger:hover {
  background: #c82333;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px 8px;
}

.category-grid-item {
  border: 0;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px;
  border-radius: 12px;
  transition: 0.15s ease;
}

.category-grid-item:hover {
  background: rgba(13, 110, 253, 0.06);
}

.category-grid-icon {
  width: 44px;
  height: 44px;
  object-fit: contain;
}

.category-grid-label {
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  color: #111;
}

.detail-carousel-wrap {
  position: relative;
}

.detail-options-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px 8px;
}

.detail-option-btn {
  border: 0;
  border-radius: 12px;
  background: transparent;
  padding: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: 0.15s ease;
}

.detail-option-btn:hover {
  background: rgba(13, 110, 253, 0.06);
}

.detail-item-icon {
  width: 48px;
  height: 48px;
  object-fit: contain;
}

.detail-label {
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  color: #111;
  line-height: 1.2;
}

.add-nav-btn {
  width: 36px;
  height: 36px;
  border: 1px solid #dfe3e8;
  border-radius: 50%;
  background: #fff;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 3;
  transition: 0.15s ease;
  color: #111;
}

.add-nav-btn:hover:not(:disabled) {
  background: #f0f4ff;
  border-color: #0d6efd;
}

.add-nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.add-nav-btn-left {
  left: -20px;
}

.add-nav-btn-right {
  right: -20px;
}

.add-params-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.add-param-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.add-param-item.add-param-full {
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
}

.add-param-label {
  font-size: 13px;
  font-weight: 700;
  color: #111;
  min-width: 90px;
}

.add-param-value {
  font-size: 14px;
  font-weight: 600;
  color: #0d6efd;
  min-width: 50px;
  text-align: right;
}

.add-param-range {
  flex: 1;
  height: 6px;
  cursor: pointer;
}

.edit-category-dropdown-wrapper {
  position: relative;
}

.edit-category-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid #eef1f4;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #111;
  cursor: pointer;
  transition: 0.15s ease;
}

.edit-category-trigger:hover {
  border-color: #0d6efd;
  background: #f8fafc;
}

.edit-category-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  background: #fff;
  border: 1px solid #eef1f4;
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  z-index: 50;
  max-height: 300px;
  overflow-y: auto;
  padding: 8px;
}

.edit-category-class-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  cursor: pointer;
  user-select: none;
  transition: 0.15s ease;
  border-radius: 12px;
  font-weight: 600;
  font-size: 14px;
}

.edit-category-class-header:hover {
  background: rgba(13, 110, 253, 0.04);
}

.edit-category-items {
  padding-left: 16px;
}

.edit-category-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: 0.1s ease;
}

.edit-category-item:hover {
  background: rgba(13, 110, 253, 0.04);
}

.edit-category-item.active {
  background: rgba(13, 110, 253, 0.08);
  color: #0d6efd;
  font-weight: 600;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.media-thumb-wrap {
  position: relative;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.media-thumb {
  width: 100%;
  height: 72px;
  object-fit: cover;
  display: block;
}

.media-del-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  line-height: 1;
  padding: 0;
}

.filter-pop-enter-active,
.filter-pop-leave-active,
.add-pop-enter-active,
.add-pop-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: bottom right;
}

.filter-pop-enter-from,
.filter-pop-leave-to,
.add-pop-enter-from,
.add-pop-leave-to {
  transform: scale(0.85);
  opacity: 0;
}

@media (max-width: 991.98px) {
  .page-title {
    font-size: 22px;
  }

  .map-card {
    height: calc(100vh - 120px);
    min-height: 400px;
  }

  .filter-panel {
    width: calc(100% - 32px);
    right: 16px;
  }

  .zoom-bottom-message {
    bottom: 78px;
    max-width: calc(100% - 28px);
    padding: 9px 16px;
    border-radius: 20px;
    font-size: 13px;
    white-space: normal;
  }

  .event-modal-card {
    width: calc(100vw - 32px);
  }

  .add-event-btn {
    padding: 0 12px 0 6px;
    gap: 6px;
  }

  .add-event-text {
    font-size: 13px;
  }

  .add-event-icon {
    width: 28px;
    height: 28px;
  }
}
</style>
