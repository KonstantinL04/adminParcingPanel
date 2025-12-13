# NLPModel.py
import pandas as pd
import re
from difflib import SequenceMatcher
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics.pairwise import cosine_similarity
from django.contrib.gis.geos import Point
from adminparcing.models import Location, Route, RoutePoint

# ------------------ Загрузка модели ------------------
try:
    vectorizer = joblib.load("adminparcing/utils/nlp/vectorizer_places.pkl")
    knn = joblib.load("adminparcing/utils/nlp/knn_places.pkl")
    print("✅ NLP модель для координат загружена!")
except:
    print("❌ Модель не найдена, нужно обучить сначала")
    vectorizer = None
    knn = None

# ------------------ Словарь мест ------------------

def load_places():
    places = {}

    for loc in Location.objects.all():
        variants = [loc.name]

        if isinstance(loc.synonyms, list):
            variants.extend(loc.synonyms)

        places[loc.name] = {
            "variants": variants,
            "lat": loc.location.y,
            "lon": loc.location.x,
        }

    return places


places_dict = load_places()

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


routes_data = load_routes()

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
def extract_partial_route(text: str, threshold=0.7):
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
                    places_dict.items(),
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
                        (p, places_dict[p]["lat"], places_dict[p]["lon"])
                        for p in partial
                    ]

    return []


# ------------------ Поиск отдельных мест ------------------
def extract_possible_places(text: str, threshold=0.7):
    found_places = []
    norm_text = normalize_text(text)
    text_words = re.findall(r'\b\w+\b', norm_text)

    for main_place, data in places_dict.items():
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
def predict_place(text: str):
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
def match_location(text: str, threshold=0.7):
    if not text or not text.strip():
        return []

    # 1️⃣ Попробовать найти кусок маршрута
    partial_route = extract_partial_route(text, threshold)
    if partial_route:
        return partial_route

    # 2️⃣ Иначе ищем отдельные места
    places_found = extract_possible_places(text, threshold)
    if places_found:
        return places_found

    # 3️⃣ Иначе используем ML модель
    lat, lon = predict_place(text)
    if lat is not None and lon is not None:
        return [("автоопределено", lat, lon)]

    return []


# matches = match_location("от поста до урика азс чисто")
# for place, lat, lon in matches:
#     print(f"{place}: {lat}, {lon}")