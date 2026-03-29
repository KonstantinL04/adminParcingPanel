<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import accidentIcon from "@/assets/accident.png";
import cameraIcon from "@/assets/camera.png";
import clearIcon from "@/assets/clear.png";
import policeIcon from "@/assets/police.png";

const mapContainer = ref(null);
const mapState = ref({ map: null, ymaps: null });

let clusterer = null;
let updateTimer = null;

const DEFAULT_CENTER = [52.329514, 104.298266];
const CATEGORY_ORDER = ["clear", "dps", "camera", "crash"];

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

function eventIcon(categoryCode) {
    const code = (categoryCode || "").toLowerCase();
    if (code === "dps") return policeIcon;
    if (code === "camera") return cameraIcon;
    if (code === "clear") return clearIcon;
    if (code === "crash") return accidentIcon;
    return null;
}

function categoryIconSrc(categoryCode) {
    const code = (categoryCode || "").toLowerCase();
    if (code === "dps") return policeIcon;
    if (code === "camera") return cameraIcon;
    if (code === "clear") return clearIcon;
    if (code === "crash") return accidentIcon;
    return policeIcon;
}

function getCategoryCodeFromGeoObject(geoObject) {
    if (!geoObject) return "other";
    if (geoObject.properties?.get) {
        return (geoObject.properties.get("category_code") || "other").toLowerCase();
    }
    return (geoObject.properties?.category_code || "other").toLowerCase();
}

function createClusterLayout(ymaps) {
    return ymaps.templateLayoutFactory.createClass("<div></div>", {
        build() {
            this.constructor.superclass.build.call(this);

            const geoObjects = this.getData()?.properties?.get("geoObjects") || [];
            const counts = { clear: 0, dps: 0, camera: 0, crash: 0, other: 0 };

            for (const geoObject of geoObjects) {
                const code = getCategoryCodeFromGeoObject(geoObject);
                if (Object.prototype.hasOwnProperty.call(counts, code)) {
                    counts[code] += 1;
                } else {
                    counts.other += 1;
                }
            }

            const parts = [];
            for (const code of CATEGORY_ORDER) {
                const count = counts[code];
                if (!count) continue;
                parts.push(`
                    <div style="display:flex;align-items:center;gap:16px;">
                        <img src="${categoryIconSrc(code)}" style="width:20px;height:20px;display:block;" />
                        <span style="font-size:16px;line-height:1;font-weight:700;color:#111;">${count}</span>
                    </div>
                `);
            }

            if (counts.other) {
                parts.push(`
                    <div style="display:flex;align-items:center;gap:4px;">
                        <span style="width:14px;height:14px;border-radius:50%;background:#ddd;display:inline-block;"></span>
                        <span style="font-size:16px;line-height:1;font-weight:700;color:#111;">${counts.other}</span>
                    </div>
                `);
            }

            const groups = parts.length || 1;
            this._width = Math.max(72, groups * 56 + 12);
            this._height = 34;

            const html = `
                <div style="
                    width:${this._width}px;
                    height:${this._height}px;
                    border-radius:17px;
                    background:#fff;
                    box-shadow:0 4px 16px rgba(0,0,0,0.22);
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    gap:8px;
                    padding:0 10px;
                    transform:translate(-50%,-50%);
                ">
                    ${parts.join("")}
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

        const icon = eventIcon(event.category_code);
        const placemark = new ymaps.Placemark(
            [lat, lon],
            {
                balloonContentHeader: event.category_label || event.category_code || "Событие",
                balloonContentBody: `
                    <div>
                        <b>Место:</b> ${event.extra_params?.place_name || "-"}<br/>
                        <b>Автор:</b> ${event.extra_params?.author_name || "-"}<br/>
                        <b>Подтверждения:</b> ${event.confirmations ?? 0}
                    </div>
                `,
                category_code: (event.category_code || "").toLowerCase(),
            },
            icon
                ? {
                    iconLayout: "default#image",
                    iconImageHref: icon,
                    iconImageSize: [28, 28],
                    iconImageOffset: [-14, -14],
                }
                : {
                    preset: eventPreset(event.category_code),
                }
        );

        placemarks.push(placemark);
    }

    return placemarks;
}

function renderEvents(events) {
    const { map, ymaps } = mapState.value;
    if (!map || !ymaps || !clusterer) return;

    const placemarks = buildPlacemarks(events, ymaps);
    clusterer.removeAll();
    clusterer.add(placemarks);
}

async function loadEvents() {
    try {
        const res = await fetch("/api/events/road-events/");
        const payload = await res.json();
        const events = normalizeEvents(payload);
        renderEvents(events);
    } catch (e) {
        console.error("Ошибка загрузки событий:", e);
    }
}

async function initMap() {
    const ymaps = await loadYandexMaps();
    const clusterLayout = createClusterLayout(ymaps);

    const map = new ymaps.Map(mapContainer.value, {
        center: DEFAULT_CENTER,
        zoom: 12,
        controls: ["zoomControl"],
    });

    clusterer = new ymaps.Clusterer({
        clusterIconLayout: clusterLayout,
        groupByCoordinates: false,
        gridSize: 128,
        minClusterSize: 2,
        clusterDisableClickZoom: false,
        clusterOpenBalloonOnClick: false,
    });

    map.geoObjects.add(clusterer);
    mapState.value = { map, ymaps };

    await loadEvents();

    updateTimer = setInterval(() => {
        if (map.action?.isActive?.()) return;
        loadEvents();
    }, 30000);
}

onMounted(async () => {
    await initMap();
});

onUnmounted(() => {
    if (updateTimer) clearInterval(updateTimer);

    const { map } = mapState.value;
    if (map) map.destroy();

    clusterer = null;
    mapState.value = { map: null, ymaps: null };
});
</script>

<template>
    <div class="container-fluid p-3 map-page">
        <h4 class="mb-3">Карта дорожных событий</h4>
        <div ref="mapContainer" class="map-box"></div>
    </div>
</template>

<style scoped>
.map-page {
    height: calc(100vh - 2rem);
    display: flex;
    flex-direction: column;
}

.map-box {
    width: 100%;
    flex: 1;
    min-height: 0;
    border: 1px solid #d0d0d0;
    border-radius: 8px;
}
</style>
