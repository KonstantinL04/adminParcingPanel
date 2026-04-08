import os
import re
from typing import Optional

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsRegressor
from django.db.models import Q

from adminparcing.models import Location
from adminparcing.utils.nlp.NLPModel import clear_model_cache

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


def _build_dataset(chat_id: int):
    qs = Location.objects.filter(Q(chat_id=chat_id) | Q(chats__id=chat_id)).distinct()
    all_place_names = []
    expanded_coords = []

    for loc in qs:
        main_place = str(loc.name)
        synonyms = loc.synonyms if isinstance(loc.synonyms, list) else []

        place_variants = [main_place]
        for syn in synonyms:
            if not syn:
                continue
            parts = re.split(r"[;,]", str(syn))
            place_variants.extend([p.strip() for p in parts if p.strip()])

        for variant in place_variants:
            if variant:
                all_place_names.append(variant)
                expanded_coords.append((loc.location.y, loc.location.x))

    return all_place_names, expanded_coords


def train_for_chat(chat_id: int) -> bool:
    os.makedirs(MODEL_DIR, exist_ok=True)
    all_place_names, expanded_coords = _build_dataset(chat_id)
    if not all_place_names:
        return False

    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
    X_vectors = vectorizer.fit_transform(all_place_names)

    knn = KNeighborsRegressor(n_neighbors=1, metric="cosine")
    knn.fit(X_vectors, expanded_coords)

    vec_path = os.path.join(MODEL_DIR, f"vectorizer_places_{chat_id}.pkl")
    knn_path = os.path.join(MODEL_DIR, f"knn_places_{chat_id}.pkl")
    joblib.dump(vectorizer, vec_path)
    joblib.dump(knn, knn_path)

    clear_model_cache(chat_id)
    return True


def train_all() -> int:
    count = 0
    chat_ids_fk = set(
        cid for cid in Location.objects.values_list("chat_id", flat=True).distinct() if cid
    )
    chat_ids_m2m = set(
        cid for cid in Location.objects.values_list("chats__id", flat=True).distinct() if cid
    )
    chat_ids = sorted(chat_ids_fk | chat_ids_m2m)
    for cid in chat_ids:
        if cid and train_for_chat(cid):
            count += 1
    return count
