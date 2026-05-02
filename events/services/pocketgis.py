import hashlib
from dataclasses import dataclass
from typing import Iterable, List


DEFAULT_CATEGORY_BY_TYPE = {
    1: "Статическая камера",
    2: "Контроль проезда на красный",
    3: "Контроль проезда на красный",
    4: "Камера средней скорости",
    5: "Контроль движения по полосе",
    6: "Видеоконтроль",
    7: "Муляж",
    8: "Мобильная засада",
    9: "Стационарный пост ДПС",
    21: "Железнодорожный переезд",
    100: "Начало населенного пункта",
    101: "Ограничение скорости",
    102: "Искусственная неровность",
    103: "Плохая дорога",
    104: "Опасный поворот",
    105: "Опасный перекресток",
    106: "Другая опасность",
    22: "Пешеходный переход",
    107: "Осторожно дети",
    108: "Конец населенного пункта",
    109: "Обгон запрещен",
}


@dataclass
class ParsedPocketGisRow:
    external_idx: int
    lon: float
    lat: float
    type_code: int
    speed_limit: int
    dir_type: int
    direction: int
    distance: int
    angle: int
    source_object_id: str
    category_name: str
    details: str


def parse_pocketgis_bytes(raw_bytes: bytes):
    text = raw_bytes.decode("cp1251", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return [], "", ""

    header = lines[0]
    source_date = header.split("//", 1)[1].strip() if "//" in header else ""
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    rows = list(_iter_rows(lines[1:]))
    return rows, source_date, file_hash


def _iter_rows(lines: Iterable[str]):
    seen_type_names = {}
    for line in lines:
        comment_idx = line.find("//")
        csv_part = line[:comment_idx].strip() if comment_idx >= 0 else line
        comment_part = line[comment_idx + 2 :].strip() if comment_idx >= 0 else ""
        if not csv_part:
            continue

        values = [v.strip() for v in csv_part.split(",")]
        if len(values) < 9:
            continue

        try:
            external_idx = int(values[0])
            lon = float(values[1])
            lat = float(values[2])
            type_code = int(values[3])
            speed_limit = int(values[4])
            dir_type = int(values[5])
            direction = int(values[6])
            distance = int(values[7])
            angle = int(values[8])
        except (TypeError, ValueError):
            continue

        tokens = [t.strip() for t in comment_part.split("|") if t.strip()]
        source_object_id = tokens[0] if tokens else ""
        category_from_comment = tokens[1] if len(tokens) > 1 else ""
        if category_from_comment and type_code not in seen_type_names:
            seen_type_names[type_code] = category_from_comment

        category_name = (
            category_from_comment
            or seen_type_names.get(type_code)
            or DEFAULT_CATEGORY_BY_TYPE.get(type_code, f"TYPE {type_code}")
        )
        details = " | ".join(tokens[2:]) if len(tokens) > 2 else ""

        yield ParsedPocketGisRow(
            external_idx=external_idx,
            lon=lon,
            lat=lat,
            type_code=type_code,
            speed_limit=speed_limit,
            dir_type=dir_type,
            direction=direction,
            distance=distance,
            angle=angle,
            source_object_id=source_object_id,
            category_name=category_name,
            details=details,
        )
