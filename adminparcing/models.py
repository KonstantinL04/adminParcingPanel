from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from adminparcing.utils.crypto import fernet
# ✔ Чаты
class Chat(models.Model):
    title = models.CharField(max_length=255)
    chat_id = models.CharField(max_length=255, unique=True)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.title


# ✔ Исключённые пользователи
class ExcludedUser(models.Model):
    value = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.value


# ✔ Категории
class AlertCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    text_patterns = models.JSONField(default=list, blank=True)
    emoji_patterns = models.JSONField(default=list, blank=True)

    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

# ✔ Словарь мест
class Location(models.Model):
    name = models.CharField(max_length=255)
    location = gis_models.PointField(default=Point(0.0, 0.0))
    synonyms = models.JSONField(default=list)

    def __str__(self):
        return self.name

# ✔ Маршруты
class Route(models.Model):
    name = models.CharField(max_length=255, unique=True)

    start_point = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="routes_start"
    )

    end_point = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="routes_end"
    )

    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

# ✔ Точки маршрута    
class RoutePoint(models.Model):
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="points"
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT
    )

    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        unique_together = ("route", "order")

    def __str__(self):
        return f"{self.route.name}: {self.order} → {self.location.name}"

# ✔ Настройки системы
class Setting(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key} = {self.value}"

# ✔ Настройки API-ключа Telegram
class SettingAPI(models.Model):
    key = models.CharField(max_length=50, unique=True)
    _value = models.BinaryField(db_column="value")

    @property
    def value(self):
        if not self._value:
            return None

        try:
            raw = bytes(self._value)          
            decrypted = fernet.decrypt(raw)
            return decrypted.decode()
        except Exception:
            return "<cannot decrypt>"

    @value.setter
    def value(self, val):
        if val is None:
            self._value = None
            return

        encrypted = fernet.encrypt(val.encode())
        self._value = encrypted               

    def __str__(self):
        return self.key