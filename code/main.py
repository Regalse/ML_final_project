"""
Основной модуль системы управления презентацией жестами.
Интегрирует распознавание жестов (AI) и управление презентацией (UI).

Запуск: python main.py
"""

import sys
import os

# Добавляем пути к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'UI'))

import time
import cv2
import numpy as np
from collections import deque
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from AI.gesture_recognition import GestureClassifier, draw_hand_skeleton, initialize_detector
from UI.presentation_controller import PresentationController
from gesture_controller import GestureController


class GesturePresentationSystem:
    """
    Основная система управления презентацией жестами.
    Интегрирует все компоненты в единый цикл работы.
    """
    
    def __init__(self, cooldown_seconds=5.0):
        """
        Инициализация системы.
        
        Args:
            cooldown_seconds: Время блокировки повторного жеста (секунды)
        """
        print("=" * 60)
        print("СИСТЕМА УПРАВЛЕНИЯ ПРЕЗЕНТАЦИЕЙ ЖЕСТАМИ")
        print("=" * 60)
        
        # Инициализация компонентов
        print("\n[1/4] Инициализация контроллера презентации...")
        self.presentation_controller = PresentationController()
        
        print("[2/4] Инициализация контроллера жестов...")
        self.gesture_controller = GestureController(self.presentation_controller)
        self.gesture_controller.COOLDOWN_SECONDS = cooldown_seconds
        
        print("[3/4] Инициализация классификатора жестов...")
        self.classifier = GestureClassifier(smoothing_window=5, confidence_threshold=0.7)
        
        print("[4/4] Инициализация детектора MediaPipe...")
        self.detector = initialize_detector()
        
        # Настройка камеры
        print("\nИнициализация захвата видео...")
        self.cap = cv2.VideoCapture(0)
        
        if not self.cap.isOpened():
            raise RuntimeError("Ошибка: не удалось подключиться к веб-камере")
        
        # Статистика производительности
        self.frame_count = 0
        self.fps = 0
        self.last_fps_time = None
        
        print("\n" + "=" * 60)
        print("СИСТЕМА ГОТОВА К РАБОТЕ")
        print("=" * 60)
        print("\nУПРАВЛЕНИЕ ЖЕСТАМИ:")
        print("  One (указательный)   → Следующий слайд")
        print("  Fist (кулак)         → Предыдущий слайд")
        print("  Open (ладонь)        → Запуск презентации")
        print("  Peace (знак мира)    → Завершение презентации")
        print(f"\nБлокировка повтора: {cooldown_seconds} сек")
        print("\nКлавиши управления:")
        print("  q - выход")
        print("  r - сброс буфера классификатора")
        print("  s - сброс всех состояний контроллера")
        print("  p - показать статистику")
        print("=" * 60 + "\n")
    
    def _calculate_fps(self):
        """Расчет FPS для мониторинга производительности."""
        current_time = None
        if self.last_fps_time is not None:
            current_time = time.time()
            elapsed = current_time - self.last_fps_time
            if elapsed > 0:
                self.fps = self.frame_count / elapsed
        
        if self.last_fps_time is None or (current_time and current_time - self.last_fps_time >= 1.0):
            self.last_fps_time = time.time()
            self.frame_count = 0
        
        self.frame_count += 1
    
    def _draw_ui_overlay(self, frame, gesture, result, status):
        """
        Отрисовка интерфейса поверх кадра.
        
        Args:
            frame: Кадр для отрисовки
            gesture: Текущий распознанный жест
            result: Результат обработки жеста из process_gesture()
            status: Статус из get_status()
        """
        h, w, _ = frame.shape
        
        # Панель информации (верхний левый угол)
        info_y = 10
        line_height = 25
        
        # Текущий жест
        gesture_color = (0, 255, 0) if result['triggered'] else (0, 255, 255) if result['blocked'] else (255, 255, 255)
        cv2.putText(frame, f"Gesture: {gesture}", (10, info_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, gesture_color, 2)
        info_y += line_height
        
        # Статус действия
        if result['triggered']:
            status_text = f"ACTION: {result['action'].upper()}"
            cv2.putText(frame, status_text, (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        elif result['blocked']:
            status_text = f"BLOCKED ({result['cooldown_remaining']:.1f}s)"
            cv2.putText(frame, status_text, (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        info_y += line_height * 2
        
        # Индикаторы cooldown для каждого действия
        cv2.putText(frame, "Cooldown Status:", (10, info_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        info_y += line_height
        
        for action_name in self.gesture_controller.GESTURE_TO_ACTION.values():
            remaining = status['cooldowns'].get(action_name, 0)
            color = (0, 0, 255) if remaining > 0 else (0, 255, 0)
            status_str = f"{remaining:.1f}s" if remaining > 0 else "READY"
            cv2.putText(frame, f"  {action_name}: {status_str}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            info_y += line_height
        
        # FPS счетчик (нижний левый угол)
        fps_text = f"FPS: {self.fps:.1f}"
        cv2.putText(frame, fps_text, (10, h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Счетчики статистики (правый верхний угол)
        stats_x = w - 200
        stats_y = 10
        cv2.putText(frame, "Statistics:", (stats_x, stats_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        stats_y += line_height
        cv2.putText(frame, f"Total: {status['stats']['total_triggers']}", (stats_x, stats_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        stats_y += line_height
        cv2.putText(frame, f"Blocked: {status['stats']['blocked_triggers']}", (stats_x, stats_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def run(self):
        """Запуск основного цикла системы."""
        import time
        
        try:
            while True:
                # Чтение кадра
                ret, frame = self.cap.read()
                if not ret:
                    print("Ошибка чтения кадра")
                    break
                
                # Расчет FPS
                self._calculate_fps()
                
                # Подготовка кадра для MediaPipe
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                h, w, _ = frame.shape
                
                # Детекция рук
                detection_result = self.detector.detect(mp_image)
                
                # Обработка обнаруженных рук
                if detection_result.hand_landmarks:
                    for idx, hand_landmarks in enumerate(detection_result.hand_landmarks):
                        # Отрисовка скелета руки
                        draw_hand_skeleton(frame, hand_landmarks, h, w)
                        
                        # Классификация жеста
                        gesture = self.classifier.get_stable_gesture(hand_landmarks)
                        
                        # Обработка жеста контроллером
                        result = self.gesture_controller.process_gesture(gesture)
                        status = self.gesture_controller.get_status()
                        
                        # Определение руки (левая/правая)
                        handedness = ""
                        if detection_result.handedness and idx < len(detection_result.handedness):
                            handedness = detection_result.handedness[idx][0].display_name
                        
                        # Отрисовка названия жеста над рукой
                        label = f"{gesture} ({handedness})"
                        cv2.putText(frame, label, (10, 30 + idx * 40),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        
                        # Отрисовка UI оверлея
                        self._draw_ui_overlay(frame, gesture, result, status)
                else:
                    # Если рук нет, просто рисуем UI
                    status = self.gesture_controller.get_status()
                    result = {'triggered': False, 'blocked': False, 'cooldown_remaining': 0, 'action': None}
                    self._draw_ui_overlay(frame, "None", result, status)
                
                # Отображение кадра
                cv2.imshow("Gesture Presentation Control", frame)
                
                # Обработка клавиш
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nВыход по команде пользователя")
                    break
                elif key == ord('r'):
                    self.classifier.reset()
                    print("Буфер классификатора сброшен")
                elif key == ord('s'):
                    self.gesture_controller.reset()
                    print("Контроллер жестов сброшен")
                elif key == ord('p'):
                    self.gesture_controller.print_statistics()
        
        except KeyboardInterrupt:
            print("\nПрервано пользователем")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Очистка ресурсов."""
        print("\nОстановка системы...")
        self.gesture_controller.print_statistics()
        self.cap.release()
        self.detector.close()
        cv2.destroyAllWindows()
        print("Ресурсы освобождены")


def main():
    """Точка входа в приложение."""
    try:
        system = GesturePresentationSystem(cooldown_seconds=5.0)
        system.run()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()