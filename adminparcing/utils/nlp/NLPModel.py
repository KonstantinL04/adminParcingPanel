# NLPModel.py
import pandas as pd
import re
from difflib import SequenceMatcher
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics.pairwise import cosine_similarity
from django.contrib.gis.geos import Point
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Q
from adminparcing.models import Location, Route, RoutePoint

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_CACHE = {}

# ------------------ Загрузка модели ------------------
try:
    vectorizer = joblib.load("adminparcing/utils/nlp/vectorizer_places.pkl")
    knn = joblib.load("adminparcing/utils/nlp/knn_places.pkl")
    print("✅ NLP модель для координат загружена!")
except Exception:
    print("❌ Модель не найдена, нужно обучить сначала")
    vectorizer = None
    knn = None


def clear_model_cache(chat_id=None):
    if chat_id is None:
        MODEL_CACHE.clear()
    else:
        MODEL_CACHE.pop(int(chat_id), None)


def _load_models_for_chat(chat_id: int):
    chat_id = int(chat_id)
    if chat_id in MODEL_CACHE:
        return MODEL_CACHE[chat_id]
    vec_path = os.path.join(MODEL_DIR, f"vectorizer_places_{chat_id}.pkl")
    knn_path = os.path.join(MODEL_DIR, f"knn_places_{chat_id}.pkl")
    if not (os.path.exists(vec_path) and os.path.exists(knn_path)):
        MODEL_CACHE[chat_id] = (None, None)
        return None, None
    try:
        v = joblib.load(vec_path)
        k = joblib.load(knn_path)
        MODEL_CACHE[chat_id] = (v, k)
        return v, k
    except Exception:
        MODEL_CACHE[chat_id] = (None, None)
        return None, None

# ------------------ Словарь мест ------------------

def load_places(chat_id=None):
    places = {}

    qs = Location.objects.prefetch_related("chats").all()
    if chat_id is not None:
        qs = qs.filter(Q(chat_id=chat_id) | Q(chats__id=chat_id)).distinct()
    for loc in qs:
        variants = [loc.name]

        if isinstance(loc.synonyms, list):
            variants.extend(loc.synonyms)

        places[loc.name] = {
            "variants": variants,
            "lat": loc.location.y,
            "lon": loc.location.x,
        }

    return places


places_dict = {}

def load_routes():
    routes = []

    qs = (
        Route.objects
        .filter(enabled=True)
        .prefetch_related("points__location")
        .select_related("start_point", "end_point")
    )

    for r in qs:
        points = [r.start_point.name]

        ordered_points = (
            RoutePoint.objects
            .filter(route=r)
            .order_by("order")
            .select_related("location")
        )

        for p in ordered_points:
            points.append(p.location.name)

        points.append(r.end_point.name)

        routes.append({
            "name": r.name,
            "points": points,
        })

    return routes


routes_data = []

def ensure_nlp_data_loaded():
    global places_dict, routes_data
    if not places_dict or not routes_data:
        try:
            if not places_dict:
                places_dict = load_places()
            if not routes_data:
                routes_data = load_routes()
        except (OperationalError, ProgrammingError):
            # DB is not ready (e.g. during migrations). Keep empty caches.
            places_dict = {}
            routes_data = []

def reload_nlp_data():
    global places_dict, routes_data
    places_dict = load_places()
    routes_data = load_routes()

# ------------------ Нормализация ------------------
def normalize_text(text: str) -> str:
    return re.sub(r'[^\w\s-]', '', text.lower().replace('ё', 'е')).strip()

area_groups = {
    "урик": ["Урик АЗС", "Урик Экономия"],
    "пост": ["КП", "город"],
}
# ------------------ Кусок маршрута ------------------
def extract_partial_route(text: str, threshold=0.7, places=None):
    ensure_nlp_data_loaded()
    places = places or places_dict
    text_lower = normalize_text(text)
    patterns = [
        r'от\s+([^\s]+(?:\s+[^\s]+)*)\s+до\s+([^\s]+(?:\s+[^\s]+)*)',
        r'([^\s]+(?:\s+[^\s]+)*)\s*-\s*([^\s]+(?:\s+[^\s]+)*)'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        for start_text, end_text in matches:
            start_text = normalize_text(start_text)
            end_text = normalize_text(end_text)

            # 🔹 Проверяем группы (например, "урик" → все связанные точки)
            def resolve_place_or_group(text_value):
                for group_name, group_points in area_groups.items():
                    if group_name in text_value:
                        return group_points
                # иначе ищем по косинусному сходству
                best_match = max(
                    places.items(),
                    key=lambda x: max(
                        cosine_similarity(
                            vectorizer.transform([text_value]),
                            vectorizer.transform(x[1]['variants'])
                        )[0]
                    )
                )[0]
                return [best_match]

            start_candidates = resolve_place_or_group(start_text)
            end_candidates = resolve_place_or_group(end_text)

            # 🔹 Ищем маршрут, где присутствует хотя бы одна пара этих точек
            for route in routes_data:
                route_points = route["points"]

                start_idx, end_idx = None, None

                for s in start_candidates:
                    if s in route_points:
                        start_idx = route_points.index(s)
                        break

                for e in end_candidates:
                    if e in route_points:
                        end_idx = route_points.index(e)
                        break

                if start_idx is not None and end_idx is not None:
                    if start_idx <= end_idx:
                        partial = route_points[start_idx:end_idx + 1]
                    else:
                        partial = route_points[end_idx:start_idx + 1][::-1]

                    return [
                        (p, places[p]["lat"], places[p]["lon"])
                        for p in partial
                    ]

    return []


# ------------------ Поиск отдельных мест ------------------
def extract_possible_places(text: str, threshold=0.7, places=None):
    ensure_nlp_data_loaded()
    places = places or places_dict
    found_places = []
    norm_text = normalize_text(text)
    text_words = re.findall(r'\b\w+\b', norm_text)

    for main_place, data in places.items():
        found = False
        for variant in data['variants']:
            variant_norm = normalize_text(variant)
            # Точное совпадение
            if re.search(r'\b' + re.escape(variant_norm) + r'\b', norm_text):
                found_places.append((main_place, data['lat'], data['lon']))
                found = True
                break
            # Частичное совпадение по словам
            if not found:
                for word in text_words:
                    sim = SequenceMatcher(None, word, variant_norm).ratio()
                    if sim >= threshold:
                        found_places.append((main_place, data['lat'], data['lon']))
                        found = True
                        break
                if found:
                    break
    return found_places

# ------------------ ML-предсказание ------------------
def predict_place(text: str, chat_id=None):
    if chat_id is not None:
        v, k = _load_models_for_chat(chat_id)
        if v is None or k is None:
            return None, None
        try:
            text_vec = v.transform([text])
            lat, lon = k.predict(text_vec)[0]
            return lat, lon
        except Exception as e:
            print(f"❌ Ошибка предсказания координат: {e}")
            return None, None
    if vectorizer is None or knn is None:
        return None, None
    try:
        text_vec = vectorizer.transform([text])
        lat, lon = knn.predict(text_vec)[0]
        return lat, lon
    except Exception as e:
        print(f"❌ Ошибка предсказания координат: {e}")
        return None, None

# ------------------ Основная функция ------------------
def match_location(text: str, threshold=0.9, chat_id=None):
    ensure_nlp_data_loaded()
    places = load_places(chat_id) if chat_id is not None else places_dict
    if not text or not text.strip():
        return []

    # 1️⃣ Попробовать найти кусок маршрута
    partial_route = extract_partial_route(text, threshold, places=places)
    if partial_route:
        return partial_route

    # 2️⃣ Иначе ищем отдельные места
    places_found = extract_possible_places(text, threshold, places=places)
    if places_found:
        return places_found

    return []


# matches = match_location("от поста до урика азс чисто")
# for place, lat, lon in matches:
#     print(f"{place}: {lat}, {lon}")
