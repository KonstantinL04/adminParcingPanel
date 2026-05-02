<script setup>
import { onMounted, onUnmounted, ref, computed, watch } from "vue";
import axios from "axios";

import defaultEventIcon from "@/assets/default.png";

const mapContainer = ref(null);
const statusText = ref("");

// Начальный центр карты — Иркутск
const INITIAL_CENTER = [52.2855, 104.2890];
const INITIAL_ZOOM = 12;

const BASE_CLUSTER_GRID_SIZE = 420;
const ZONE_MIN_ZOOM = 15;

// Минимальный зум для загрузки точек (при слишком широком bbox — слишком много данных)
const LOAD_MIN_ZOOM = 10;

let map = null;
let ymapsRef = null;
let clusterer = null;
let zoneCollection = null;
let editCollection = null;
// markerStates теперь Map: pointId -> state, для быстрого поиска при обновлении
let markerStatesMap = new Map();
// Для совместимости с кодом, который итерирует markerStates
let markerStates = [];
let clusterLayoutClass = null;
let clusterUpdateTimer = null;
let bboxLoadTimer = null;
let isClustererOnMap = false;
let lastLoadedBbox = null; // { minLon, minLat, maxLon, maxLat }

// Отслеживаем текущий зум реактивно
const currentZoom = ref(INITIAL_ZOOM);
const isLowZoom = computed(() => currentZoom.value < ZONE_MIN_ZOOM);
const showZoomMessage = computed(() => !clusterModeActive.value && isLowZoom.value);

// Состояние загрузки
const isLoading = ref(true);
const isBboxLoading = ref(false);
// true = кластеры включены, false = все маркеры отдельно
const clusterModeActive = ref(true);
const showPointModal = ref(false);
const selectedPointState = ref(null);
const isEditMode = ref(false);
const availableCategories = ref([]);
const editForm = ref({
  category_id: null,
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

/* ---- filters ---- */
const showFilterPanel = ref(false);
const appliedCategoryFilters = ref([]);
const draftCategoryFilters = ref([]);
const filtersInitialized = ref(false);

/* filterOptions строится из данных точек */
const filterOptions = computed(() => {
  const map = new Map();
  for (const item of markerStates) {
    const p = item.point;
    const key = categoryKeyForPocketPoint(p);
    if (map.has(key)) continue;
    const icon = p.category_icon ? resolveMediaUrl(p.category_icon) : defaultEventIcon;
    map.set(key, {
      key,
      label: p.category_name || p.type_code || "PocketGIS",
      icon,
    });
  }
  return Array.from(map.values()).sort((a, b) =>
    a.label.localeCompare(b.label, "ru")
  );
});

/* ---------------- helpers ---------------- */

function resolveMediaUrl(path) {
  if (!path) return defaultEventIcon;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return path.startsWith("/") ? path : `/${path}`;
}

function normalizeCategoryCode(value) {
  return String(value || "").trim().toLowerCase();
}

function categoryKeyForPocketPoint(point) {
  if (point?.category) return `pocket:${point.category}`;
  const code = normalizeCategoryCode(
    point?.type_code || point?.category_name || point?.category
  );
  return `pocket-code:${code || "other"}`;
}

function getPlacemarkCategoryKey(geoObject) {
  if (geoObject?.properties?.get) {
    return geoObject.properties.get("category_key") || "other";
  }
  return "other";
}

function getPlacemarkIcon(geoObject) {
  if (geoObject?.properties?.get) {
    return geoObject.properties.get("category_icon") || defaultEventIcon;
  }
  return defaultEventIcon;
}

function getCategoryMetaById(id) {
  const cid = Number(id);
  if (!Number.isFinite(cid)) return null;
  return availableCategories.value.find((c) => Number(c.id) === cid) || null;
}

function getCategoryIconById(id) {
  const meta = getCategoryMetaById(id);
  const iconPath = meta?.icon || meta?.image || meta?.category_icon || meta?.icon_file || meta?.marker || meta?.file || null;
  return iconPath ? resolveMediaUrl(iconPath) : defaultEventIcon;
}

function applyPlacemarkIcon(placemark, iconHref, isDraggable = false) {
  if (!placemark) return;
  const safeIcon = iconHref || defaultEventIcon;
  placemark.options.set("iconLayout", "default#image");
  placemark.options.set("iconImageHref", safeIcon);
  const [w, h] = isDraggable ? [32, 32] : [24, 24];
  placemark.options.set("iconImageSize", [w, h]);
  placemark.options.set("iconImageOffset", [-w / 2, -h]);
  if (isDraggable) {
    placemark.options.set("iconShape", {
      type: "Rectangle",
      coordinates: [
        [-w / 2, -h],
        [w / 2, 0],
      ],
    });
  } else {
    placemark.options.set("iconShape", null);
  }
}

function createPocketPlacemark(point, lat, lon, icon, draggable = false) {
  const [w, h] = draggable ? [32, 32] : [24, 24];
  const placemark = new ymapsRef.Placemark(
    [lat, lon],
    {
      category_key: categoryKeyForPocketPoint(point),
      category_icon: icon,
    },
    {
      draggable,
      dragCursor: "move",
      cursor: draggable ? "move" : "pointer",
      interactivityModel: "default#geoObject",
      pane: "places",
      zIndex: draggable ? 10000 : 0,
      zIndexHover: draggable ? 10001 : 1,
      zIndexActive: draggable ? 10002 : 1,
      hasBalloon: false,
      openBalloonOnClick: false,
      iconLayout: "default#image",
      iconImageHref: icon || defaultEventIcon,
      iconImageSize: [w, h],
      iconImageOffset: [-w / 2, -h],
      iconShape: draggable
        ? {
            type: "Rectangle",
            coordinates: [
              [-w / 2, -h],
              [w / 2, 0],
            ],
          }
        : undefined,
    }
  );
  applyPlacemarkIcon(placemark, icon, draggable);
  return placemark;
}

function updatePlacemarkMeta(placemark, point, icon, isDraggable = false) {
  if (!placemark) return;
  applyPlacemarkIcon(placemark, icon, isDraggable);
  placemark.properties.set("category_key", categoryKeyForPocketPoint(point));
  placemark.properties.set("category_icon", icon);
}

/* ---------------- maps ---------------- */

function loadYandexMaps() {
  return new Promise((resolve, reject) => {
    if (window.ymaps) {
      window.ymaps.ready(() => resolve(window.ymaps));
      return;
    }
    const apiKey = import.meta.env.VITE_YANDEX_MAPS_API_KEY;
    const script = document.createElement("script");
    script.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`;
    script.async = true;
    script.onload = () => window.ymaps.ready(() => resolve(window.ymaps));
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

/* ---------------- cluster layout ---------------- */

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
      const isFarZoom = zoom <= 11;
      const isMidZoom = zoom > 11 && zoom <= 13;

      const maxItemsPerRow = isFarZoom ? 3 : isMidZoom ? 4 : 5;
      const maxVisibleGroups = isFarZoom ? 6 : isMidZoom ? 8 : 12;

      const groups = allGroups.slice(0, maxVisibleGroups);
      const hidden = Math.max(0, allGroups.length - groups.length);

      const itemWidth = isFarZoom ? 42 : 46;
      const rowHeight = isFarZoom ? 22 : 24;

      const rows = [];
      for (let i = 0; i < groups.length; i += maxItemsPerRow) {
        rows.push(groups.slice(i, i + maxItemsPerRow));
      }
      if (hidden > 0) {
        const tail = { count: `+${hidden}`, icon: null };
        if (!rows.length || rows[rows.length - 1].length >= maxItemsPerRow) rows.push([tail]);
        else rows[rows.length - 1].push(tail);
      }

      const cols = Math.min(maxItemsPerRow, groups.length || 1);
      this._width = Math.max(68, cols * itemWidth + 12);
      this._height = Math.max(30, rows.length * rowHeight + 8);

      const rowsHtml = rows
        .map(
          (row) => `
<div style="display:flex;align-items:center;justify-content:center;gap:8px;min-height:${rowHeight}px;">
${row.map((g) => `
<div style="display:flex;align-items:center;gap:5px;min-width:${itemWidth - 6}px;justify-content:center;">
${g.icon ? `<img src="${g.icon}" style="width:14px;height:14px;" />` : ""}
<span style="font-size:13px;font-weight:700;color:#111;">${g.count}</span>
</div>`).join("")}
</div>`
        )
        .join("");

      this.getParentElement().innerHTML = `
<div style="
width:${this._width}px;
height:${this._height}px;
border-radius:15px;
background:#fff;
box-shadow:0 4px 16px rgba(0,0,0,.22);
display:flex;
flex-direction:column;
align-items:center;
justify-content:center;
padding:4px 6px;
transform:translate(-50%,-50%);
">${rowsHtml}</div>`;
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

function createClusterer() {
  clusterLayoutClass = createClusterLayout(ymapsRef);
  clusterer = new ymapsRef.Clusterer({
    clusterIconLayout: clusterLayoutClass,
    groupByCoordinates: false,
    gridSize: BASE_CLUSTER_GRID_SIZE,
    minClusterSize: 2,
    clusterDisableClickZoom: false,
    clusterOpenBalloonOnClick: false,
  });
  map.geoObjects.add(clusterer);
  isClustererOnMap = true;
  clusterer.options.set("gridSize", calcClusterGridSizeByZoom(map.getZoom()));
}

/* ---------------- zones ---------------- */

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
  for (let i = 0; i <= steps; i++) {
    const az = normalizeAngle360(start + (diff * i) / steps);
    points.push(destinationByDistanceAndBearing(lat, lon, az, distance));
  }
  points.push([lat, lon]);
  return points;
}

function drawZones() {
  if (!map || !zoneCollection) return;
  zoneCollection.removeAll();
  if (map.getZoom() < ZONE_MIN_ZOOM) return;

  for (const item of markerStates) {
    if (!item.visible) continue;
    const isEditingSelected = isEditMode.value && selectedPointState.value === item;

    if (clusterModeActive.value && !isEditingSelected) {
      const state = clusterer ? clusterer.getObjectState(item.placemark) : null;
      if (state && (!state.isShown || state.isClustered)) continue;
    }

    const zoneLat = isEditingSelected ? Number(editForm.value.lat) : item.lat;
    const zoneLon = isEditingSelected ? Number(editForm.value.lon) : item.lon;
    if (!Number.isFinite(zoneLat) || !Number.isFinite(zoneLon)) continue;

    const p = item.point;
    const zoneDirection = isEditingSelected ? Number(editForm.value.direction || 0) : Number(p.direction || 0);
    const zoneAngle = isEditingSelected ? Number(editForm.value.angle || 0) : Number(p.angle || 0);
    const zoneDistance = isEditingSelected ? Number(editForm.value.distance || 0) : Number(p.distance || 0);
    const zoneDirType = isEditingSelected ? Number(editForm.value.dir_type || 1) : Number(p.dir_type || 1);
    if (!Number.isFinite(zoneDistance) || zoneDistance <= 0) continue;

    const addZone = (direction) => {
      const polygon = new ymapsRef.GeoObject(
        {
          geometry: {
            type: "Polygon",
            coordinates: [buildSectorPoints(zoneLat, zoneLon, direction, zoneAngle, zoneDistance)],
          },
        },
        {
          fillColor: "rgba(33,150,243,.22)",
          strokeColor: "rgba(33,150,243,.55)",
          strokeWidth: 1.5,
          interactivityModel: "default#silent",
          pane: "areas",
          zIndex: 0,
        }
      );
      zoneCollection.add(polygon);
    };

    addZone(zoneDirection);
    if (zoneDirType === 2) addZone(zoneDirection + 180);
  }
}

/* ---------------- filters ---------------- */

function ensureFilterState() {
  const keys = filterOptions.value.map((o) => o.key);
  if (!keys.length) return;

  if (!filtersInitialized.value) {
    appliedCategoryFilters.value = [...keys];
    draftCategoryFilters.value = [...keys];
    filtersInitialized.value = true;
    return;
  }

  const keysSet = new Set(keys);
  // Новые категории добавляем автоматически как включённые
  const newKeys = keys.filter((k) => !appliedCategoryFilters.value.includes(k));
  if (newKeys.length) {
    appliedCategoryFilters.value = [...appliedCategoryFilters.value, ...newKeys];
    draftCategoryFilters.value = [...draftCategoryFilters.value, ...newKeys];
  }

  // Удаляем несуществующие
  appliedCategoryFilters.value = appliedCategoryFilters.value.filter((k) => keysSet.has(k));
  draftCategoryFilters.value = draftCategoryFilters.value.filter((k) => keysSet.has(k));
}

function toggleFilterPanel() {
  if (showFilterPanel.value) {
    showFilterPanel.value = false;
    return;
  }
  draftCategoryFilters.value = [...appliedCategoryFilters.value];
  showFilterPanel.value = true;
}

function toggleDraftCategory(key) {
  const set = new Set(draftCategoryFilters.value);
  if (set.has(key)) set.delete(key);
  else set.add(key);
  draftCategoryFilters.value = filterOptions.value.map((o) => o.key).filter((k) => set.has(k));
}

function applyCategoryFilters() {
  appliedCategoryFilters.value = [...draftCategoryFilters.value];
  showFilterPanel.value = false;
  rebuildVisibleObjects();
}

function resetCategoryFilters() {
  const keys = filterOptions.value.map((o) => o.key);
  draftCategoryFilters.value = [...keys];
  appliedCategoryFilters.value = [...keys];
  showFilterPanel.value = false;
  rebuildVisibleObjects();
}

function toggleClusterMode() {
  clusterModeActive.value = !clusterModeActive.value;
  rebuildVisibleObjects();
}

function focusMapOnPoint(state) {
  if (!map || !state) return;
  const coords = [
    Number(isEditMode.value ? editForm.value.lat : state.lat),
    Number(isEditMode.value ? editForm.value.lon : state.lon),
  ];
  if (!coords.every(Number.isFinite)) return;

  const targetZoom = Math.max(Number(map.getZoom()) || 0, ZONE_MIN_ZOOM + 1);
  requestAnimationFrame(() => {
    try {
      map.container.fitToViewport();
      currentZoom.value = targetZoom;
      map.setCenter(coords, targetZoom);
      setTimeout(drawZones, 0);
    } catch (e) {
      console.error("Не удалось приблизить карту к метке:", e);
    }
  });
}

function getEditIcon() {
  const selectedIcon = getCategoryIconById(editForm.value.category_id);
  if (selectedIcon && selectedIcon !== defaultEventIcon) return selectedIcon;
  return selectedPointState.value?.point?.category_icon
    ? resolveMediaUrl(selectedPointState.value.point.category_icon)
    : defaultEventIcon;
}

function buildEditPointSnapshot(state) {
  const catMeta = getCategoryMetaById(editForm.value.category_id);
  return {
    ...state.point,
    category: Number(editForm.value.category_id) || state.point.category,
    category_name: catMeta?.name || state.point.category_name,
  };
}

let isDragging = false;
let _editDragActive = false;
let _pendingDragCheck = false;

function getEditPlacemarkPixelBounds() {
  const state = selectedPointState.value;
  if (!state?.editPlacemark || !map) return null;
  try {
    const coords = state.editPlacemark.geometry.getCoordinates();
    if (!coords) return null;
    const proj = map.options.get("projection");
    const globalPx = map.converter.globalToPage(
      proj.toGlobalPixels(coords, map.getZoom())
    );
    const containerEl = mapContainer.value;
    if (!containerEl) return null;
    const rect = containerEl.getBoundingClientRect();
    const px = globalPx[0] + rect.left;
    const py = globalPx[1] + rect.top;
    return { left: px - 16, right: px + 16, top: py - 32, bottom: py };
  } catch (_) {
    return null;
  }
}

function isPointInEditPlacemark(clientX, clientY) {
  const b = getEditPlacemarkPixelBounds();
  if (!b) return false;
  return clientX >= b.left - 6 && clientX <= b.right + 6 &&
         clientY >= b.top - 6  && clientY <= b.bottom + 6;
}

function onEventsPane_mousedown(e) {
  if (!isEditMode.value) return;
  if (isPointInEditPlacemark(e.clientX, e.clientY)) {
    e.stopPropagation();
    e.preventDefault();
    _pendingDragCheck = true;
    disableMapDrag();
    startManualDrag(e);
  }
}

function onEventsPane_touchstart(e) {
  if (!isEditMode.value || !e.touches.length) return;
  const t = e.touches[0];
  if (isPointInEditPlacemark(t.clientX, t.clientY)) {
    e.stopPropagation();
    e.preventDefault();
    _pendingDragCheck = true;
    disableMapDrag();
    startManualDrag(t);
  }
}

let _manualDragStarted = false;

function startManualDrag(pointerEvent) {
  _manualDragStarted = false;
  const onMove = (ev) => {
    const cx = ev.clientX ?? ev.touches?.[0]?.clientX;
    const cy = ev.clientY ?? ev.touches?.[0]?.clientY;
    if (cx == null) return;
    if (!_manualDragStarted) {
      _manualDragStarted = true;
      _editDragActive = true;
      isDragging = true;
    }
    const containerEl = mapContainer.value;
    if (!containerEl || !map) return;
    const rect = containerEl.getBoundingClientRect();
    const localX = cx - rect.left;
    const localY = cy - rect.top;
    try {
      const proj = map.options.get("projection");
      const zoom = map.getZoom();
      const globalPx = map.converter.pageToGlobal([localX, localY]);
      const geoCoords = proj.fromGlobalPixels(globalPx, zoom);
      const state = selectedPointState.value;
      if (state?.editPlacemark && geoCoords) {
        state.editPlacemark.geometry.setCoordinates(geoCoords);
        editForm.value.lat = Number(geoCoords[0]);
        editForm.value.lon = Number(geoCoords[1]);
        drawZones();
      }
    } catch (_) {}
  };

  const onUp = () => {
    window.removeEventListener("mousemove", onMove);
    window.removeEventListener("mouseup", onUp);
    window.removeEventListener("touchmove", onMove);
    window.removeEventListener("touchend", onUp);
    _pendingDragCheck = false;
    if (_editDragActive) {
      _editDragActive = false;
      isDragging = false;
      enableMapDrag();
      drawZones();
    } else {
      enableMapDrag();
    }
    _manualDragStarted = false;
  };

  window.addEventListener("mousemove", onMove, { passive: false });
  window.addEventListener("mouseup", onUp);
  window.addEventListener("touchmove", onMove, { passive: false });
  window.addEventListener("touchend", onUp);
}

let _eventsPaneEl = null;

function attachMapContainerGuard() {
  setTimeout(() => {
    const container = mapContainer.value;
    if (!container) return;
    _eventsPaneEl = container.querySelector("[class*='events-pane']");
    if (_eventsPaneEl) {
      _eventsPaneEl.addEventListener("mousedown", onEventsPane_mousedown, { capture: true });
      _eventsPaneEl.addEventListener("touchstart", onEventsPane_touchstart, { capture: true, passive: false });
    }
    window.addEventListener("mouseup", onWindowMouseUp, { capture: true });
  }, 500);
}

function detachMapContainerGuard() {
  if (_eventsPaneEl) {
    _eventsPaneEl.removeEventListener("mousedown", onEventsPane_mousedown, { capture: true });
    _eventsPaneEl.removeEventListener("touchstart", onEventsPane_touchstart, { capture: true });
    _eventsPaneEl = null;
  }
  window.removeEventListener("mouseup", onWindowMouseUp, { capture: true });
}

function onWindowMouseUp() {
  if (isDragging || _editDragActive) {
    isDragging = false;
    _editDragActive = false;
    enableMapDrag();
  }
}

const DRAG_BEHAVIORS = ["drag", "scrollZoom", "multiTouch"];

function disableMapDrag() {
  if (!map?.behaviors) return;
  for (const b of DRAG_BEHAVIORS) {
    try { map.behaviors.disable(b); } catch (_) {}
  }
}

function enableMapDrag() {
  if (!map?.behaviors) return;
  for (const b of DRAG_BEHAVIORS) {
    try { map.behaviors.enable(b); } catch (_) {}
  }
}

function removeEditPlacemark(state) {
  if (!state?.editPlacemark) return;
  state.editPlacemark.events.remove("dragstart", onEditPlacemarkDragStart);
  state.editPlacemark.events.remove("dragend", onEditPlacemarkDragEnd);
  state.editPlacemark.events.remove("drag", onSelectedPlacemarkDrag);
  if (editCollection) editCollection.remove(state.editPlacemark);
  else if (map) map.geoObjects.remove(state.editPlacemark);
  state.editPlacemark = null;
  if (isDragging) {
    isDragging = false;
    enableMapDrag();
  }
}

function onEditPlacemarkDragStart() {
  if (!isDragging) {
    isDragging = true;
    disableMapDrag();
  }
}

function onEditPlacemarkDragEnd() {
  if (isDragging) {
    isDragging = false;
    enableMapDrag();
  }
  drawZones();
}

function ensureEditPlacemark(state) {
  if (!map || !state) return null;
  if (!state.editPlacemark) {
    const editPoint = buildEditPointSnapshot(state);
    state.editPlacemark = createPocketPlacemark(
      editPoint,
      Number(editForm.value.lat),
      Number(editForm.value.lon),
      getEditIcon(),
      true
    );
    state.editPlacemark.events.add("dragstart", onEditPlacemarkDragStart);
    state.editPlacemark.events.add("dragend", onEditPlacemarkDragEnd);
    state.editPlacemark.events.add("drag", onSelectedPlacemarkDrag);
  }
  updatePlacemarkMeta(state.editPlacemark, buildEditPointSnapshot(state), getEditIcon(), true);
  state.editPlacemark.geometry.setCoordinates([
    Number(editForm.value.lat),
    Number(editForm.value.lon),
  ]);
  return state.editPlacemark;
}

function openPointModal(pointState) {
  selectedPointState.value = pointState;
  const p = pointState.point;
  editForm.value = {
    category_id: Number(p.category ?? 0) || null,
    speed_limit: Number(p.speed_limit || 0),
    direction: Number(p.direction || 0),
    dir_type: Number(p.dir_type || 1),
    distance: Number(p.distance || 0),
    angle: Number(p.angle || 25),
    lat: Number(pointState.lat),
    lon: Number(pointState.lon),
  };
  modalError.value = "";
  isEditMode.value = false;
  showPointModal.value = true;
}

function closePointModal() {
  const wasEditing = isEditMode.value;
  const state = selectedPointState.value;
  if (state) {
    removeEditPlacemark(state);
  }
  showPointModal.value = false;
  selectedPointState.value = null;
  isEditMode.value = false;
  modalBusy.value = false;
  modalError.value = "";
  if (wasEditing && state) rebuildVisibleObjects();
}

function applyPointEditsLocally() {
  if (!selectedPointState.value) return;
  const state = selectedPointState.value;
  const p = state.point;
  
  const localIcon = getCategoryIconById(editForm.value.category_id);
  
  p.category = Number(editForm.value.category_id) || p.category;
  const catMeta = getCategoryMetaById(editForm.value.category_id);
  if (catMeta?.name) p.category_name = catMeta.name;
  p.speed_limit = Number(editForm.value.speed_limit);
  p.direction = Number(editForm.value.direction);
  p.dir_type = Number(editForm.value.dir_type) === 2 ? 2 : 1;
  p.distance = Number(editForm.value.distance);
  p.angle = Number(editForm.value.angle);
  const lat = Number(editForm.value.lat);
  const lon = Number(editForm.value.lon);
  state.lat = lat;
  state.lon = lon;
  p.location = { ...(p.location || {}), type: "Point", coordinates: [lon, lat] };
  state.placemark.geometry.setCoordinates([lat, lon]);

  const finalIcon = (localIcon !== defaultEventIcon) 
      ? localIcon 
      : (p.category_icon ? resolveMediaUrl(p.category_icon) : defaultEventIcon);
      
  p.category_icon = finalIcon;
  updatePlacemarkMeta(state.placemark, p, finalIcon);
}

watch(
  () => [editForm.value.direction, editForm.value.speed_limit, editForm.value.angle, editForm.value.distance, editForm.value.dir_type],
  () => {
    if (!isEditMode.value || !selectedPointState.value) return;
    const p = selectedPointState.value.point;
    p.direction = Number(editForm.value.direction);
    p.speed_limit = Number(editForm.value.speed_limit);
    p.angle = Number(editForm.value.angle);
    p.distance = Number(editForm.value.distance);
    p.dir_type = Number(editForm.value.dir_type) === 2 ? 2 : 1;
    drawZones();
  }
);

watch(
  () => editForm.value.category_id,
  (newCategoryId) => {
    if (!isEditMode.value || !selectedPointState.value) return;
    const state = selectedPointState.value;
    const icon = getCategoryIconById(newCategoryId);
    const catMeta = getCategoryMetaById(newCategoryId);
    const previewPoint = {
      ...state.point,
      category: Number(newCategoryId) || state.point.category,
      category_name: catMeta?.name || state.point.category_name,
      category_icon: icon
    };
    updatePlacemarkMeta(state.editPlacemark, previewPoint, icon, true);
    drawZones();
  }
);

function toggleEditMode(enabled) {
  modalError.value = "";
  const state = selectedPointState.value;
  if (!state?.placemark?.options) return;
  isEditMode.value = enabled;
  if (enabled) {
    ensureEditPlacemark(state);
    rebuildVisibleObjects();
    focusMapOnPoint(state);
    drawZones();
  } else {
    removeEditPlacemark(state);
    rebuildVisibleObjects();
  }
}

function onSelectedPlacemarkDrag() {
  const state = selectedPointState.value;
  const placemark = state?.editPlacemark || state?.placemark;
  if (!placemark?.geometry) return;
  const coords = placemark.geometry.getCoordinates();
  if (!Array.isArray(coords) || coords.length !== 2) return;
  editForm.value.lat = Number(coords[0]);
  editForm.value.lon = Number(coords[1]);
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
      const payload = {
        category: Number(editForm.value.category_id) || null,
        speed_limit: Number(editForm.value.speed_limit),
        direction: Number(editForm.value.direction),
        dir_type: Number(editForm.value.dir_type) === 2 ? 2 : 1,
        distance: Number(editForm.value.distance),
        angle: Number(editForm.value.angle),
        location: {
          type: "Point",
          coordinates: [Number(editForm.value.lon), Number(editForm.value.lat)],
        },
      };
      const response = await axios.patch(`/api/events/pocketgis/points/${id}/`, payload);
      if (response && response.data) {
        Object.assign(state.point, response.data);
      }
    }

    applyPointEditsLocally();

    const newKey = categoryKeyForPocketPoint(state.point);
    if (appliedCategoryFilters.value.length > 0 && !appliedCategoryFilters.value.includes(newKey)) {
      appliedCategoryFilters.value.push(newKey);
      draftCategoryFilters.value.push(newKey);
    }

    toggleEditMode(false);
    rebuildVisibleObjects();
  } catch (e) {
    modalError.value = e?.response?.data?.detail || "Не удалось сохранить событие";
  } finally {
    modalBusy.value = false;
  }
}

async function loadCategories() {
  try {
    const { data } = await axios.get("/api/events/pocketgis/categories/");
    availableCategories.value = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error("Ошибка загрузки категорий:", e);
    availableCategories.value = [];
  }
}

async function deletePoint() {
  if (!selectedPointState.value) return;
  if (!window.confirm("Удалить это событие?")) return;

  modalBusy.value = true;
  modalError.value = "";
  try {
    const state = selectedPointState.value;
    const id = state.point?.id;
    if (id) {
      await axios.delete(`/api/events/pocketgis/points/${id}/`);
    }
    // Удаляем из Map и массива
    if (id) markerStatesMap.delete(String(id));
    markerStates = markerStates.filter((item) => item !== state);
    removeEditPlacemark(state);
    ensureFilterState();
    rebuildVisibleObjects();
    closePointModal();
  } catch (e) {
    modalError.value = e?.response?.data?.detail || "Не удалось удалить событие";
  } finally {
    modalBusy.value = false;
  }
}

function rebuildVisibleObjects() {
  if (!map) return;
  if (isDragging) return;

  if (clusterer) clusterer.removeAll();
  if (editCollection) editCollection.removeAll();

  const active = new Set(appliedCategoryFilters.value);
  const editingState = isEditMode.value ? selectedPointState.value : null;
  const shouldShowClusterer = clusterModeActive.value;

  if (clusterer) {
    if (shouldShowClusterer && !isClustererOnMap) {
      map.geoObjects.add(clusterer);
      isClustererOnMap = true;
    } else if (!shouldShowClusterer && isClustererOnMap) {
      map.geoObjects.remove(clusterer);
      isClustererOnMap = false;
    }
  }

  markerStates.forEach((item) => {
    map.geoObjects.remove(item.placemark);
    const key = categoryKeyForPocketPoint(item.point);
    item.visible = !active.size || active.has(key);
    if (!item.visible) return;

    if (editingState === item) {
      const editPlacemark = ensureEditPlacemark(item);
      if (editPlacemark && editCollection) editCollection.add(editPlacemark);
      return;
    }

    if (!clusterModeActive.value && isLowZoom.value) {
      return;
    }

    if (!clusterModeActive.value) map.geoObjects.add(item.placemark);
    else clusterer.add(item.placemark);
  });

  drawZones();
}

/* ---------------- traffic ---------------- */

function addTrafficControl() {
  if (!map || !ymapsRef) return;
  const trafficControl = new ymapsRef.control.TrafficControl({
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
}

/* ---------------- bbox loading ---------------- */

/**
 * Получить bbox текущего вида карты с небольшим запасом (20%)
 */
function getMapBbox(paddingFactor = 0.2) {
  if (!map) return null;
  const bounds = map.getBounds();
  if (!bounds) return null;
  const [[minLat, minLon], [maxLat, maxLon]] = bounds;
  const latPad = (maxLat - minLat) * paddingFactor;
  const lonPad = (maxLon - minLon) * paddingFactor;
  return {
    minLon: minLon - lonPad,
    minLat: minLat - latPad,
    maxLon: maxLon + lonPad,
    maxLat: maxLat + latPad,
  };
}

/**
 * Проверяем, достаточно ли текущий bbox выходит за пределы ранее загруженного,
 * чтобы стоило делать новый запрос.
 */
function needsReload(bbox) {
  if (!lastLoadedBbox) return true;
  const lb = lastLoadedBbox;
  // Перезагружаем если видимая область вышла за загруженный bbox
  return (
    bbox.minLon < lb.minLon ||
    bbox.minLat < lb.minLat ||
    bbox.maxLon > lb.maxLon ||
    bbox.maxLat > lb.maxLat
  );
}

/**
 * Загрузить точки по текущему bbox и заменить все точки на карте.
 */
async function loadPointsByBbox() {
  if (!map) return;
  const zoom = map.getZoom();
  if (zoom < LOAD_MIN_ZOOM) {
    // На слишком мелком зуме не грузим — слишком много данных
    return;
  }

  // bbox с запасом 20% для плавной прокрутки без перезагрузки
  const bbox = getMapBbox(0.2);
  if (!bbox) return;

  // Не перезагружаем если вышли только в рамках уже загруженного bbox
  if (!needsReload(bbox)) return;

  isBboxLoading.value = true;

  try {
    const bboxStr = `${bbox.minLon},${bbox.minLat},${bbox.maxLon},${bbox.maxLat}`;
    let offset = 0;
    const limit = 5000;
    const loaded = [];

    // Загружаем все страницы (обычно одна при разумном bbox)
    while (true) {
      const { data } = await axios.get("/api/events/pocketgis/points/", {
        params: { bbox: bboxStr, limit, offset },
      });
      const rows = Array.isArray(data?.results) ? data.results : [];
      loaded.push(...rows);
      offset += rows.length;
      if (!rows.length || offset >= (data?.count ?? 0)) break;
    }

    // Запоминаем загруженный bbox (с запасом, чтобы не перегружать при небольших движениях)
    lastLoadedBbox = bbox;

    // Применяем новые точки: заменяем всё
    applyNewPoints(loaded);

    statusText.value = `Точек: ${markerStates.length}`;
  } catch (e) {
    console.error("Ошибка загрузки точек по bbox:", e);
  } finally {
    isBboxLoading.value = false;
  }
}

/**
 * Заменить весь набор точек на карте новым списком.
 * Точки, которых больше нет — удаляем. Новые — добавляем.
 * Существующие — обновляем данные (без пересоздания placemark).
 */
function applyNewPoints(points) {
  if (!map) return;

  const newIds = new Set(points.map((p) => String(p.id)));
  const editingState = selectedPointState.value;

  // Удаляем точки, которых нет в новом наборе
  // (кроме редактируемой — её не трогаем)
  const toRemove = markerStates.filter(
    (item) => !newIds.has(String(item.point.id)) && item !== editingState
  );
  for (const item of toRemove) {
    if (clusterer) clusterer.remove(item.placemark);
    map.geoObjects.remove(item.placemark);
    markerStatesMap.delete(String(item.point.id));
  }
  markerStates = markerStates.filter((item) => !toRemove.includes(item));

  // Добавляем/обновляем точки из нового набора
  const toAddToClusterer = [];

  for (const point of points) {
    const key = String(point.id);
    const existing = markerStatesMap.get(key);

    if (existing) {
      // Обновляем данные (кроме редактируемой точки)
      if (existing !== editingState) {
        Object.assign(existing.point, point);
        const coords = point.location.coordinates;
        existing.lat = Number(coords[1]);
        existing.lon = Number(coords[0]);
        existing.placemark.geometry.setCoordinates([existing.lat, existing.lon]);
        const icon = point.category_icon ? resolveMediaUrl(point.category_icon) : defaultEventIcon;
        updatePlacemarkMeta(existing.placemark, point, icon);
      }
    } else {
      // Создаём новую
      const coords = point.location.coordinates;
      const lon = Number(coords[0]);
      const lat = Number(coords[1]);
      const icon = point.category_icon ? resolveMediaUrl(point.category_icon) : defaultEventIcon;

      const placemark = createPocketPlacemark(point, lat, lon, icon);
      const state = { point, placemark, editPlacemark: null, lat, lon, visible: true };
      placemark.events.add("click", () => openPointModal(state));

      markerStates.push(state);
      markerStatesMap.set(key, state);
      toAddToClusterer.push(placemark);
    }
  }

  // Обновляем фильтры с новыми категориями
  ensureFilterState();

  // Перестраиваем видимые объекты
  // Добавляем новые плейсмарки в clusterer/карту
  if (toAddToClusterer.length) {
    const active = new Set(appliedCategoryFilters.value);
    for (const state of markerStates) {
      if (!toAddToClusterer.includes(state.placemark)) continue;
      const catKey = categoryKeyForPocketPoint(state.point);
      state.visible = !active.size || active.has(catKey);
      if (!state.visible) continue;
      if (clusterModeActive.value) {
        // будет добавлено ниже через clusterer.add
      } else if (!isLowZoom.value) {
        map.geoObjects.add(state.placemark);
      }
    }
    if (clusterModeActive.value) {
      const visibleNew = toAddToClusterer.filter((pm) => {
        const s = markerStates.find((x) => x.placemark === pm);
        return s?.visible;
      });
      if (visibleNew.length) clusterer.add(visibleNew);
    }
  }

  drawZones();
}

/* ---------------- init ---------------- */

async function initMap() {
  ymapsRef = await loadYandexMaps();
  await loadCategories();

  map = new ymapsRef.Map(mapContainer.value, {
    center: INITIAL_CENTER,
    zoom: INITIAL_ZOOM,
    controls: ["zoomControl"],
  });

  currentZoom.value = map.getZoom();

  createClusterer();
  addTrafficControl();
  attachMapContainerGuard();

  zoneCollection = new ymapsRef.GeoObjectCollection();
  map.geoObjects.add(zoneCollection);

  editCollection = new ymapsRef.GeoObjectCollection();
  map.geoObjects.add(editCollection);

  // Первая загрузка точек по текущему bbox
  await loadPointsByBbox();

  map.events.add("boundschange", () => {
    if (isDragging) return;

    if (clusterUpdateTimer) clearTimeout(clusterUpdateTimer);
    if (bboxLoadTimer) clearTimeout(bboxLoadTimer);

    clusterUpdateTimer = setTimeout(() => {
      if (isDragging) return;
      const newZoom = map.getZoom();
      const prevZoom = currentZoom.value;
      currentZoom.value = newZoom;

      if (clusterModeActive.value) {
        clusterer.options.set("gridSize", calcClusterGridSizeByZoom(newZoom));
        drawZones();
      } else {
        const prevLow = prevZoom < ZONE_MIN_ZOOM;
        const newLow = newZoom < ZONE_MIN_ZOOM;
        if (prevLow !== newLow) {
          rebuildVisibleObjects();
        } else {
          drawZones();
        }
      }
    }, 90);

    // Загрузка новых точек с дебаунсом 600мс
    bboxLoadTimer = setTimeout(() => {
      if (isDragging) return;
      loadPointsByBbox();
    }, 600);
  });
}

onMounted(async () => {
  try {
    await initMap();
  } catch (e) {
    console.error("Ошибка карты:", e);
    statusText.value = "Ошибка карты";
  } finally {
    isLoading.value = false;
  }
});

onUnmounted(() => {
  if (clusterUpdateTimer) clearTimeout(clusterUpdateTimer);
  if (bboxLoadTimer) clearTimeout(bboxLoadTimer);
  detachMapContainerGuard();
  if (map) map.destroy();
});
</script>

<template>
  <div class="container-fluid p-3 map-page">
    <h4 class="mb-3">Карта</h4>

    <div class="map-wrap">
      <div ref="mapContainer" class="map-box"></div>

      <!-- Оверлей загрузки -->
      <div v-if="isLoading" class="map-overlay">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Загрузка...</span>
        </div>
        <div class="mt-2 text-white fw-semibold">Загрузка данных...</div>
      </div>

      <!-- Индикатор подгрузки по bbox -->
      <div v-if="!isLoading && isBboxLoading" class="bbox-loading-indicator">
        <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
        <span class="ms-2 small">Загрузка точек...</span>
      </div>

      <!-- Оверлей сообщения о необходимости приближения -->
      <div v-if="showZoomMessage" class="map-overlay zoom-message">
        <div class="zoom-message-text">
          Приблизьте, чтобы увидеть дорожные события
        </div>
      </div>

      <!-- Кнопка фильтров -->
      <div class="map-controls-right">
        <button
          class="round-control"
          type="button"
          @click="toggleFilterPanel"
          title="Фильтры"
        >
          <i class="bi bi-sliders"></i>
        </button>
      </div>

      <!-- Панель фильтров -->
      <transition name="filter-pop">
        <div v-if="showFilterPanel" class="filter-panel card shadow">
          <div class="card-body p-3">
            <div class="filter-item filter-item-cluster mb-1" @click="toggleClusterMode">
              <div class="filter-label-wrap">
                <i class="bi bi-diagram-3 filter-cluster-icon"></i>
                <span class="filter-label">Кластеризация</span>
              </div>
              <button
                class="filter-check"
                :class="{ active: clusterModeActive }"
                type="button"
              >
                <i v-if="clusterModeActive" class="bi bi-check-lg"></i>
              </button>
            </div>

            <div class="filter-divider mb-2"></div>

            <div class="filter-list">
              <div
                v-for="item in filterOptions"
                :key="item.key"
                class="filter-item"
                @click="toggleDraftCategory(item.key)"
              >
                <div class="filter-label-wrap">
                  <img :src="item.icon" alt="" class="filter-icon" />
                  <span class="filter-label">{{ item.label }}</span>
                </div>
                <button
                  class="filter-check"
                  :class="{ active: draftCategoryFilters.includes(item.key) }"
                  type="button"
                >
                  <i v-if="draftCategoryFilters.includes(item.key)" class="bi bi-check-lg"></i>
                </button>
              </div>
            </div>

            <div class="filter-actions d-flex justify-content-end gap-2 mt-3">
              <button
                type="button"
                class="btn btn-secondary btn-sm rounded-pill px-3 filter-action-btn"
                @click="resetCategoryFilters"
              >
                Сбросить
              </button>
              <button
                type="button"
                class="btn btn-primary btn-sm rounded-pill px-3 filter-action-btn"
                @click="applyCategoryFilters"
              >
                Применить
              </button>
            </div>
          </div>
        </div>
      </transition>

      <div v-if="showPointModal" class="event-floating-panel" @click.stop>
        <div class="event-modal-card" @click.stop>
          <div class="event-modal-header">
            <h5 class="mb-0">{{ selectedPointState?.point?.category_name || selectedPointState?.point?.type_code || "Событие" }}</h5>
            <button class="close-btn" @click.stop="closePointModal">×</button>
          </div>

          <div class="event-modal-body">
            <template v-if="!isEditMode">
              <div class="info-row"><span>Скоростной лимит:</span><strong>{{ editForm.speed_limit }} км/ч</strong></div>
              <div class="info-row"><span>Координаты:</span><strong>{{ editForm.lat }}, {{ editForm.lon }}</strong></div>
              <div class="info-row"><span>Азимут:</span><strong>{{ editForm.direction }}</strong></div>
              <div class="info-row"><span>Направление:</span><strong>{{ editForm.dir_type === 2 ? "В обе стороны" : "В одну сторону" }}</strong></div>
              <div class="info-row"><span>Дистанция:</span><strong>{{ editForm.distance }} м</strong></div>
              <div class="info-row"><span>Угол:</span><strong>{{ editForm.angle }}°</strong></div>
            </template>

            <template v-else>
              <div class="mb-2">
                <label class="form-label mb-1">Категория</label>
                <select v-model.number="editForm.category_id" class="form-select form-select-sm">
                  <option :value="null">Не выбрано</option>
                  <option v-for="cat in availableCategories" :key="cat.id" :value="cat.id">
                    {{ cat.name }}
                  </option>
                </select>
              </div>
              <div class="text-muted small mb-2">Широта/долгота меняются перетаскиванием метки на карте.</div>
              <div class="row g-2">
                <div class="col-6">
                  <label class="form-label mb-1">Широта</label>
                  <input :value="editForm.lat" type="number" step="0.000001" class="form-control form-control-sm" disabled />
                </div>
                <div class="col-6">
                  <label class="form-label mb-1">Долгота</label>
                  <input :value="editForm.lon" type="number" step="0.000001" class="form-control form-control-sm" disabled />
                </div>
                <div class="col-6">
                  <label class="form-label mb-1">Скоростной лимит: {{ editForm.speed_limit }} км/ч</label>
                  <input v-model.number="editForm.speed_limit" type="range" min="0" max="200" step="1" class="form-range" />
                </div>
                <div class="col-6">
                  <label class="form-label mb-1">Азимут: {{ editForm.direction }}°</label>
                  <input v-model.number="editForm.direction" type="range" min="0" max="360" step="1" class="form-range" />
                </div>
                <div class="col-6">
                  <label class="form-label mb-1">Угол: {{ editForm.angle }}°</label>
                  <input v-model.number="editForm.angle" type="range" min="1" max="180" step="1" class="form-range" />
                </div>
                <div class="col-6">
                  <label class="form-label mb-1">Дистанция: {{ editForm.distance }} м</label>
                  <input v-model.number="editForm.distance" type="range" min="50" max="2000" step="10" class="form-range" />
                </div>
                <div class="col-6">
                  <label class="form-label mb-1 d-block">Направление</label>
                  <div class="form-check form-switch mt-2">
                    <input
                      id="dirTypeSwitch"
                      class="form-check-input"
                      type="checkbox"
                      :checked="editForm.dir_type === 2"
                      @change="editForm.dir_type = $event.target.checked ? 2 : 1"
                    />
                    <label class="form-check-label" for="dirTypeSwitch">
                      {{ editForm.dir_type === 2 ? "В обе стороны" : "В одну сторону" }}
                    </label>
                  </div>
                </div>
              </div>
            </template>

            <div v-if="modalError" class="alert alert-danger py-2 px-3 mt-3 mb-0">{{ modalError }}</div>
          </div>

          <div class="event-modal-actions">
            <template v-if="!isEditMode">
              <button class="btn btn-warning" @click.stop="toggleEditMode(true)">Редактировать</button>
              <button class="btn btn-danger" :disabled="modalBusy" @click.stop="deletePoint">Удалить</button>
            </template>
            <template v-else>
              <button class="btn btn-secondary" :disabled="modalBusy" @click.stop="toggleEditMode(false)">Отмена</button>
              <button class="btn btn-primary" :disabled="modalBusy" @click.stop="savePoint">Сохранить</button>
            </template>
          </div>
        </div>
      </div>
    </div>

    <div v-if="statusText" class="small text-primary mt-2">{{ statusText }}</div>
  </div>
</template>

<style scoped>
/* ---- layout ---- */
.map-page {
  height: calc(100vh - 2rem);
  min-height: 640px;
  display: flex;
  flex-direction: column;
}

.map-wrap {
  position: relative;
  flex: 1;
  min-height: 520px;
}

.map-box {
  width: 100%;
  height: 100%;
  min-height: 520px;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
}

/* ---- overlay (загрузка и сообщение) ---- */
.map-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  border-radius: 8px;
  z-index: 15;
  pointer-events: none;
}

.zoom-message {
  background: rgba(0, 0, 0, 0.25);
}

.zoom-message-text {
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  padding: 12px 24px;
  border-radius: 12px;
  font-size: 18px;
  font-weight: 500;
  text-align: center;
  max-width: 280px;
}

/* ---- индикатор подгрузки bbox ---- */
.bbox-loading-indicator {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  top: 10px;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 20px;
  padding: 6px 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  z-index: 20;
  display: flex;
  align-items: center;
  pointer-events: none;
}

/* ---- controls (правый угол) ---- */
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
  cursor: pointer;
}

/* ---- filter panel ---- */
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
  flex-shrink: 0;
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

.filter-divider {
  height: 1px;
  background: #e5e5e5;
  margin: 0 -4px;
}

.filter-cluster-icon {
  font-size: 20px;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2f89e0;
}

.filter-item-cluster {
  padding-bottom: 2px;
}

.event-floating-panel {
  position: absolute;
  left: 16px;
  bottom: 16px;
  z-index: 30;
  pointer-events: none;
}

.event-modal-card {
  width: min(520px, calc(100vw - 320px));
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  pointer-events: auto;
}

.event-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #ececec;
}

.event-modal-body {
  padding: 14px 16px;
}

.event-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px 16px;
}

.close-btn {
  width: 34px;
  height: 34px;
  border: 0;
  background: transparent;
  font-size: 28px;
  line-height: 1;
  color: #666;
  cursor: pointer;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px dashed #eee;
}
</style>