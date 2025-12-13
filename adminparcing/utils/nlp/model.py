# train_model.py
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsRegressor
import joblib
import re

# Загружаем CSV
points_df = pd.read_csv("points.csv")

# Создаем расширенный список мест с синонимами
all_place_names = []
expanded_coords = []

for _, row in points_df.iterrows():
    main_place = str(row["place"])
    synonyms = str(row["synonyms"])
    
    # Разбиваем синонимы по разделителям
    place_variants = [main_place]
    if synonyms and synonyms != "nan":
        syn_list = re.split(r'[;,]', synonyms)
        place_variants.extend([syn.strip() for syn in syn_list if syn.strip()])
    
    # Добавляем все варианты в обучающие данные
    for variant in place_variants:
        if variant:
            all_place_names.append(variant)
            expanded_coords.append((row["lat"], row["lon"]))

# Векторизация текста
vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2,4))
X_vectors = vectorizer.fit_transform(all_place_names)

# Обучение KNN
knn = KNeighborsRegressor(n_neighbors=1, metric='cosine')
knn.fit(X_vectors, expanded_coords)

# Сохранение модели
joblib.dump(vectorizer, "vectorizer_places.pkl")
joblib.dump(knn, "knn_places.pkl")
print("✅ Модель для координат обучена и сохранена!")