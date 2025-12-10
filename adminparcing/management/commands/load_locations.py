import csv
from django.contrib.gis.geos import Point
from adminparcing.models import Location
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    with open("adminparcing/management/commands/points.csv", newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["place"].strip()
            lat = float(row["lat"])
            lon = float(row["lon"])

            # ---- разбор синонимов ----
            raw_syn = row.get("synonyms", "").strip()
            if raw_syn:
                # убрать кавычки и разделить
                raw_syn = raw_syn.replace('"', '')
                synonyms = [s.strip() for s in raw_syn.split(";") if s.strip()]
            else:
                synonyms = []

            # ---- запись в БД ----
            Location.objects.update_or_create(
                name=name,
                defaults={
                    "location": Point(lon, lat),  # GIS: сначала X=lon, потом Y=lat
                    "synonyms": synonyms,
                }
            )

    print("✅ Готово! Все точки загружены в таблицу Location")