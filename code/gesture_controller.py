"""
Менеджер жестов для управления презентацией (Gesture Controller)
Этап 3: Интеграция системы распознавания жестов с управлением презентацией

[TASK-3.1] Архитектура менеджера событий: класс GestureController, маппинг жестов и действий.
[TASK-3.2] Реализация логики состояний: защита от повторного срабатывания.
[TASK-3.3] Интеграция в главный цикл: обеспечение производительности.
"""

import time
from typing import Dict, Optional, Callable
from datetime import datetime


class GestureController:
    """
    Центральный контроллер для управления презентацией через жесты.
    
    Ответственности:
    - Маппинг жестов на действия презентации
    - Защита от повторного срабатывания (cooldown)
    - Логирование событий
    - Предоставление статуса для визуальной обратной связи
    """
    
    DEFAULT_GESTURE_TO_ACTION: Dict[str, str] = {
        "One": "next_slide",
        "Fist": "prev_slide",
        "Open": "start_presentation",
        "Peace": "end_presentation",
    }

    COOLDOWN_SECONDS = 5.0

    def __init__(self, presentation_controller, gesture_mapping: Dict[str, str] | None = None,
                 cooldown_seconds: float = 5.0):
        """
        Инициализация контроллера жестов.

        Args:
            presentation_controller: Экземпляр PresentationController для выполнения действий
            gesture_mapping: Маппинг жестов на действия (из config.json)
            cooldown_seconds: Время блокировки повторного срабатывания
        """
        self.presentation_controller = presentation_controller
        self.GESTURE_TO_ACTION = dict(gesture_mapping or self.DEFAULT_GESTURE_TO_ACTION)
        self.COOLDOWN_SECONDS = cooldown_seconds
        self.enabled = False

        self._last_triggered: Dict[str, float] = {}
        self._gesture_counts: Dict[str, int] = {gesture: 0 for gesture in self.GESTURE_TO_ACTION.keys()}
        self._total_triggers = 0
        self._blocked_triggers = 0
        self.current_gesture = "None"
        self.last_result: Dict = {}
        self._last_update_time = time.time()

        print("[GestureController] Инициализирован")
        print(f"[GestureController] Маппинг жестов: {self.GESTURE_TO_ACTION}")
        print(f"[GestureController] Cooldown: {self.COOLDOWN_SECONDS} сек")
    
    def _get_action_for_gesture(self, gesture: str) -> Optional[str]:
        """
        Получение названия действия для жеста.
        
        Args:
            gesture: Название распознанного жеста
            
        Returns:
            Название действия или None если жест не распознан
        """
        return self.GESTURE_TO_ACTION.get(gesture)
    
    def _is_on_cooldown(self, action: str) -> bool:
        """
        Проверка, находится ли действие на блокировке (cooldown).
        
        Args:
            action: Название действия для проверки
            
        Returns:
            True если действие заблокировано, False иначе
        """
        if action not in self._last_triggered:
            return False
        
        elapsed = time.time() - self._last_triggered[action]
        return elapsed < self.COOLDOWN_SECONDS
    
    def _get_remaining_cooldown(self, action: str) -> float:
        """
        Получение оставшегося времени блокировки для действия.
        
        Args:
            action: Название действия
            
        Returns:
            Оставшееся время в секундах (0 если не заблокировано)
        """
        if action not in self._last_triggered:
            return 0.0
        
        elapsed = time.time() - self._last_triggered[action]
        remaining = self.COOLDOWN_SECONDS - elapsed
        return max(0.0, remaining)
    
    def _execute_action(self, action: str):
        """
        Выполнение действия через PresentationController.
        
        Args:
            action: Название действия для выполнения
        """
        action_method = getattr(self.presentation_controller, action, None)
        if action_method and callable(action_method):
            action_method()
            self._last_triggered[action] = time.time()
            self._total_triggers += 1
        else:
            print(f"[GestureController] Ошибка: действие '{action}' не найдено")
    
    def update_mapping(self, gesture_mapping: Dict[str, str]) -> None:
        """Обновление маппинга жестов без перезапуска системы."""
        self.GESTURE_TO_ACTION = dict(gesture_mapping)
        for gesture in self.GESTURE_TO_ACTION:
            self._gesture_counts.setdefault(gesture, 0)
        print(f"[GestureController] Маппинг обновлён: {self.GESTURE_TO_ACTION}")

    def set_cooldown(self, seconds: float) -> None:
        self.COOLDOWN_SECONDS = seconds

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        state = "включено" if enabled else "выключено"
        print(f"[GestureController] Слежение {state}")

    def process_gesture(self, gesture: str) -> Dict:
        """
        Обработка распознанного жеста.
        
        Основной метод, который вызывается из главного цикла для каждого кадра.
        
        Args:
            gesture: Название распознанного жеста из системы AI
            
        Returns:
            Dict с информацией о результате обработки:
            - 'triggered': bool, было ли выполнено действие
            - 'action': str|None, название выполненного действия
            - 'blocked': bool, было ли действие заблокировано
            - 'cooldown_remaining': float, оставшееся время блокировки
            - 'message': str, человекочитаемое сообщение
        """
        self.current_gesture = gesture
        result = {
            'triggered': False,
            'action': None,
            'blocked': False,
            'cooldown_remaining': 0.0,
            'message': '',
            'tracking_enabled': self.enabled,
        }

        if not self.enabled:
            result['message'] = 'Слежение остановлено'
            self.last_result = result
            return result

        action = self._get_action_for_gesture(gesture)
        
        if action is None:
            result['message'] = f"Жест '{gesture}' не имеет привязанного действия"
            self.last_result = result
            return result
        
        # Проверяем блокировку
        if self._is_on_cooldown(action):
            remaining = self._get_remaining_cooldown(action)
            result['blocked'] = True
            result['cooldown_remaining'] = remaining
            result['message'] = f"Действие '{action}' заблокировано ({remaining:.1f} сек)"
            self._blocked_triggers += 1
            self.last_result = result
            return result

        # Выполняем действие
        self._execute_action(action)
        result['triggered'] = True
        result['action'] = action
        result['message'] = f"Выполнено действие: {action}"
        
        # Обновляем статистику
        self._gesture_counts[gesture] = self._gesture_counts.get(gesture, 0) + 1
        
        print(f"[GestureController] {result['message']}")
        self.last_result = result
        return result
    
    def get_status(self) -> Dict:
        """
        Получение текущего статуса контроллера для отображения.
        
        Returns:
            Dict со статусной информацией:
            - current_gesture: текущий жест
            - cooldowns: dict с оставшимся временем блокировки по действиям
            - stats: статистика срабатываний
        """
        cooldowns = {}
        for action in self._last_triggered.keys():
            remaining = self._get_remaining_cooldown(action)
            if remaining > 0:
                cooldowns[action] = remaining
        
        return {
            'current_gesture': self.current_gesture,
            'cooldowns': cooldowns,
            'stats': {
                'total_triggers': self._total_triggers,
                'blocked_triggers': self._blocked_triggers,
                'gesture_counts': self._gesture_counts.copy()
            }
        }
    
    def reset(self):
        """Сброс всех состояний контроллера."""
        self._last_triggered.clear()
        self._gesture_counts = {gesture: 0 for gesture in self.GESTURE_TO_ACTION.keys()}
        self._total_triggers = 0
        self._blocked_triggers = 0
        self.current_gesture = "None"
        print("[GestureController] Сброшен")
    
    def print_statistics(self):
        """Вывод статистики работы контроллера."""
        print("\n" + "=" * 60)
        print("GESTURE CONTROLLER - СТАТИСТИКА РАБОТЫ")
        print("=" * 60)
        print(f"Всего срабатываний: {self._total_triggers}")
        print(f"Заблокировано повторов: {self._blocked_triggers}")
        print("\nСрабатывания по жестам:")
        for gesture, count in self._gesture_counts.items():
            action = self.GESTURE_TO_ACTION.get(gesture, "N/A")
            print(f"  {gesture:10} → {action:20} : {count} раз")
        print("=" * 60 + "\n")
