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
    
    # Маппинг жестов на названия действий
    GESTURE_TO_ACTION: Dict[str, str] = {
        "One": "next_slide",      # Указательный палец - следующий слайд
        "Fist": "prev_slide",     # Кулак - предыдущий слайд
        "Open": "start_presentation",  # Открытая ладонь - запуск презентации
        "Peace": "end_presentation"    # Знак мира - завершение презентации
    }
    
    # Время блокировки повторного срабатывания того же жеста (в секундах)
    COOLDOWN_SECONDS = 5.0
    
    def __init__(self, presentation_controller):
        """
        Инициализация контроллера жестов.
        
        Args:
            presentation_controller: Экземпляр PresentationController для выполнения действий
        """
        self.presentation_controller = presentation_controller
        
        # Словарь для хранения времени последнего срабатывания каждого действия
        # Формат: {action_name: timestamp}
        self._last_triggered: Dict[str, float] = {}
        
        # Счетчики статистики
        self._gesture_counts: Dict[str, int] = {gesture: 0 for gesture in self.GESTURE_TO_ACTION.keys()}
        self._total_triggers = 0
        self._blocked_triggers = 0
        
        # Текущий активный жест (для отображения)
        self.current_gesture = "None"
        
        # Время последнего обновления (для расчета cooldown)
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
            'message': ''
        }
        
        # Получаем действие для жеста
        action = self._get_action_for_gesture(gesture)
        
        if action is None:
            # Жест не распознан или не имеет привязанного действия
            result['message'] = f"Жест '{gesture}' не имеет привязанного действия"
            return result
        
        # Проверяем блокировку
        if self._is_on_cooldown(action):
            remaining = self._get_remaining_cooldown(action)
            result['blocked'] = True
            result['cooldown_remaining'] = remaining
            result['message'] = f"Действие '{action}' заблокировано ({remaining:.1f} сек)"
            self._blocked_triggers += 1
            return result
        
        # Выполняем действие
        self._execute_action(action)
        result['triggered'] = True
        result['action'] = action
        result['message'] = f"Выполнено действие: {action}"
        
        # Обновляем статистику
        self._gesture_counts[gesture] = self._gesture_counts.get(gesture, 0) + 1
        
        print(f"[GestureController] {result['message']}")
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
