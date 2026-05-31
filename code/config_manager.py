"""
Менеджер конфигурации приложения (Этап 4, TASK-4.1).

Загрузка и сохранение настроек из config.json.
"""

import json
import os
from copy import deepcopy
from typing import Any, Dict


AVAILABLE_GESTURES = [
    "One", "Fist", "Open", "Peace",
    "Pinky", "Shaka", "Three", "Four",
]

AVAILABLE_ACTIONS = [
    "next_slide",
    "prev_slide",
    "start_presentation",
    "end_presentation",
    "none",
]

ACTION_LABELS = {
    "next_slide": "Следующий слайд",
    "prev_slide": "Предыдущий слайд",
    "start_presentation": "Запуск презентации",
    "end_presentation": "Завершение презентации",
    "none": "Без действия",
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "gesture_mapping": {
        "One": "next_slide",
        "Fist": "prev_slide",
        "Open": "start_presentation",
        "Peace": "end_presentation",
    },
    "cooldown_seconds": 5.0,
    "smoothing_window": 5,
    "confidence_threshold": 0.7,
    "camera_index": 0,
}


def get_project_root() -> str:
    """Корневая директория проекта (на уровень выше code/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_path() -> str:
    return os.path.join(get_project_root(), "config.json")


class ConfigManager:
    """Загрузка, валидация и сохранение конфигурации."""

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or get_config_path()
        self._config = deepcopy(DEFAULT_CONFIG)
        self.load()

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    def load(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self._config = self._merge_with_defaults(loaded)
        else:
            self._config = deepcopy(DEFAULT_CONFIG)
            self.save()
        return self._config

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def update(self, new_config: Dict[str, Any]) -> None:
        self._config = self._merge_with_defaults(new_config)
        self.save()

    def get_gesture_mapping(self) -> Dict[str, str]:
        mapping = self._config.get("gesture_mapping", {})
        return {k: v for k, v in mapping.items() if v and v != "none"}

    def _merge_with_defaults(self, loaded: Dict[str, Any]) -> Dict[str, Any]:
        merged = deepcopy(DEFAULT_CONFIG)
        merged.update({k: v for k, v in loaded.items() if k != "gesture_mapping"})

        if "gesture_mapping" in loaded:
            merged["gesture_mapping"] = {
                **DEFAULT_CONFIG["gesture_mapping"],
                **loaded["gesture_mapping"],
            }

        merged["cooldown_seconds"] = float(merged["cooldown_seconds"])
        merged["smoothing_window"] = int(merged["smoothing_window"])
        merged["confidence_threshold"] = float(merged["confidence_threshold"])
        merged["camera_index"] = int(merged["camera_index"])
        return merged
