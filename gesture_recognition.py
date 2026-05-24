# Система распознавания жестов на основе MediaPipe Hands
# Этап 1: Создать систему распознавания жестов
# [TASK-1.1] Инициализация захвата видео: подключение к веб-камере, цикл чтения кадров.
# [TASK-1.2] Интеграция MediaPipe Hands: настройка детекции и отрисовка скелета руки.
# [TASK-1.3] Разработка логики классификации жестов: анализ ключевых точек, программирование базовых жестов.
# [TASK-1.4] Фильтрация шумов и стабильность: усреднение, порог срабатывания.

import cv2
import numpy as np
from collections import deque
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- 1. Определение связей (каркаса кисти) ---
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),  # Большой палец
    (0, 5), (5, 6), (6, 7), (7, 8),  # Указательный палец
    (5, 9), (9, 10), (10, 11), (11, 12),  # Средний палец
    (9, 13), (13, 14), (14, 15), (15, 16),  # Безымянный палец
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)  # Мизинец и основание
]

# Индексы ключевых точек для каждого пальца
FINGER_TIPS = [4, 8, 12, 16, 20]  # Кончики пальцев: большой, указательный, средний, безымянный, мизинец
FINGER_PIPS = [3, 6, 10, 14, 18]  # Вторые фаланги
FINGER_MCPS = [2, 5, 9, 13, 17]   # Основания пальцев (MCP суставы)


class GestureClassifier:
    """Класс для классификации жестов на основе ключевых точек руки."""
    
    def __init__(self, smoothing_window=5, confidence_threshold=0.7):
        """
        Инициализация классификатора.
        
        Args:
            smoothing_window: Размер окна для усреднения результатов (TASK-1.4)
            confidence_threshold: Порог уверенности для срабатывания жеста (TASK-1.4)
        """
        self.smoothing_window = smoothing_window
        self.confidence_threshold = confidence_threshold
        
        # Буфер для сглаживания результатов (TASK-1.4)
        self.gesture_buffer = deque(maxlen=smoothing_window)
        self.current_gesture = "None"
        
    def _is_finger_extended(self, landmarks, finger_idx):
        """
        Проверка, выпрямлен ли палец.
        
        Args:
            landmarks: Список ключевых точек руки
            finger_idx: Индекс пальца (0-большой, 1-указательный, 2-средний, 3-безымянный, 4-мизинец)
            
        Returns:
            bool: True если палец выпрямлен
        """
        if finger_idx == 0:  # Большой палец - особая логика
            # Сравниваем положение кончика большого пальца с MCP суставом
            tip_x = landmarks[FINGER_TIPS[0]].x
            mcp_x = landmarks[FINGER_MCPS[0]].x
            
            # Для правой и левой руки разное направление
            return abs(tip_x - mcp_x) > 0.05
        else:
            # Для остальных пальцев: кончик выше чем PIP сустав (в координатах Y меньше)
            tip_y = landmarks[FINGER_TIPS[finger_idx]].y
            pip_y = landmarks[FINGER_PIPS[finger_idx]].y
            mcp_y = landmarks[FINGER_MCPS[finger_idx]].y
            
            # Палец выпрямлен если кончик выше PIP и PIP выше MCP
            return tip_y < pip_y and pip_y < mcp_y
    
    def _count_extended_fingers(self, landmarks):
        """Подсчет количества выпрямленных пальцев."""
        count = 0
        for i in range(5):
            if self._is_finger_extended(landmarks, i):
                count += 1
        return count
    
    def classify(self, landmarks):
        """
        Классификация жеста по ключевым точкам (TASK-1.3).
        
        Args:
            landmarks: Ключевые точки руки
            
        Returns:
            tuple: (название жеста, уверенность)
        """
        extended_count = self._count_extended_fingers(landmarks)
        
        # Базовые жесты
        gesture = "None"
        confidence = 0.5
        
        if extended_count == 0:
            gesture = "Fist"  # Кулак
            confidence = 0.8
        elif extended_count == 1:
            # Проверяем какой палец выпрямлен
            if self._is_finger_extended(landmarks, 1):  # Указательный
                gesture = "One"  # Один палец / указание
                confidence = 0.85
            elif self._is_finger_extended(landmarks, 4):  # Мизинец
                gesture = "Pinky"  # Мизинец
                confidence = 0.75
        elif extended_count == 2:
            if self._is_finger_extended(landmarks, 1) and self._is_finger_extended(landmarks, 2):
                gesture = "Peace"  # Знак мира (V)
                confidence = 0.9
            elif self._is_finger_extended(landmarks, 0) and self._is_finger_extended(landmarks, 4):
                gesture = "Shaka"  # Шака (большой + мизинец)
                confidence = 0.8
        elif extended_count == 3:
            if (self._is_finger_extended(landmarks, 1) and 
                self._is_finger_extended(landmarks, 2) and 
                self._is_finger_extended(landmarks, 3)):
                gesture = "Three"  # Три пальца
                confidence = 0.85
        elif extended_count == 4:
            gesture = "Four"  # Четыре пальца
            confidence = 0.85
        elif extended_count == 5:
            gesture = "Open"  # Открытая ладонь
            confidence = 0.9
        
        return gesture, confidence
    
    def get_stable_gesture(self, landmarks):
        """
        Получение стабильного жеста с фильтрацией шумов (TASK-1.4).
        
        Args:
            landmarks: Ключевые точки руки
            
        Returns:
            str: Стабильное название жеста
        """
        gesture, confidence = self.classify(landmarks)
        
        # Добавляем в буфер только если уверенность выше порога
        if confidence >= self.confidence_threshold:
            self.gesture_buffer.append(gesture)
        
        # Возвращаем наиболее частый жест из буфера
        if len(self.gesture_buffer) > 0:
            gestures = list(self.gesture_buffer)
            most_common = max(set(gestures), key=gestures.count)
            self.current_gesture = most_common
        
        return self.current_gesture
    
    def reset(self):
        """Сброс буфера сглаживания."""
        self.gesture_buffer.clear()
        self.current_gesture = "None"


def initialize_detector():
    """Инициализация детектора рук MediaPipe (TASK-1.2)."""
    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )
    return vision.HandLandmarker.create_from_options(options)


def draw_hand_skeleton(frame, landmarks, h, w):
    """Отрисовка скелета руки (TASK-1.2)."""
    # Отрисовка соединений (линии)
    for pt1_idx, pt2_idx in HAND_CONNECTIONS:
        pt1 = landmarks[pt1_idx]
        pt2 = landmarks[pt2_idx]
        cv2.line(frame,
                 (int(pt1.x * w), int(pt1.y * h)),
                 (int(pt2.x * w), int(pt2.y * h)),
                 (255, 255, 255), 2)
    
    # Отрисовка ключевых точек
    for i, lm in enumerate(landmarks):
        color = (0, 0, 255)  # Красный для всех точек
        if i in FINGER_TIPS:
            color = (0, 255, 0)  # Зеленый для кончиков пальцев
        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 6, color, -1)


def main():
    """Основная функция системы распознавания жестов."""
    
    # [TASK-1.1] Инициализация захвата видео
    print("Инициализация захвата видео...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Ошибка: не удалось подключиться к веб-камере")
        return
    
    # [TASK-1.2] Интеграция MediaPipe Hands
    print("Инициализация детектора MediaPipe Hands...")
    detector = initialize_detector()
    
    # [TASK-1.3] Инициализация классификатора жестов
    classifier = GestureClassifier(smoothing_window=5, confidence_threshold=0.7)
    
    print("Запуск системы распознавания жестов...")
    print("Жесты: Fist, One, Two(Peace), Three, Four, Open, Pinky, Shaka")
    print("Нажмите 'q' для выхода, 'r' для сброса буфера")
    
    frame_count = 0
    
    try:
        # [TASK-1.1] Цикл чтения кадров
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Ошибка чтения кадра")
                break
            
            frame_count += 1
            
            # [TASK-1.2] Подготовка кадра для MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = vision.Image(image_format=vision.ImageFormat.SRGB, data=frame_rgb)
            h, w, _ = frame.shape
            
            # Запуск детекции
            detection_result = detector.detect(mp_image)
            
            # Обработка результатов
            if detection_result.hand_landmarks:
                for idx, hand_landmarks in enumerate(detection_result.hand_landmarks):
                    # Отрисовка скелета руки
                    draw_hand_skeleton(frame, hand_landmarks, h, w)
                    
                    # [TASK-1.3] Классификация жеста
                    # [TASK-1.4] Получение стабильного жеста с фильтрацией
                    gesture = classifier.get_stable_gesture(hand_landmarks)
                    
                    # Определение руки (левая/правая)
                    handedness = ""
                    if detection_result.handedness and idx < len(detection_result.handedness):
                        handedness = detection_result.handedness[idx][0].display_name
                    
                    # Отрисовка названия жеста
                    label = f"{gesture} ({handedness})"
                    cv2.putText(frame, label, (10, 30 + idx * 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Отображение информации о системе
            cv2.putText(frame, f"FPS: {frame_count}", (10, frame.shape[0] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow("Hand Gesture Recognition", frame)
            
            # Обработка клавиш
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                classifier.reset()
                print("Буфер сглаживания сброшен")
    
    except KeyboardInterrupt:
        print("\nОстановка системы...")
    
    finally:
        # Освобождение ресурсов
        cap.release()
        detector.close()
        cv2.destroyAllWindows()
        print("Ресурсы освобождены")


if __name__ == "__main__":
    main()
