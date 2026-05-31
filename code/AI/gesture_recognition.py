# Система распознавания жестов на основе MediaPipe Hands
# Этап 1: Создать систему распознавания жестов
# Этап 5: Оптимизация точности и расширение библиотеки жестов

import math
from collections import deque

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
]

FINGER_TIPS = [4, 8, 12, 16, 20]
FINGER_PIPS = [3, 6, 10, 14, 18]
FINGER_MCPS = [2, 5, 9, 13, 17]

THUMB_IP = 3


class GestureClassifier:
    """Классификация жестов с учётом handedness и нормализованных порогов."""

    THUMB_SIDE_THRESHOLD = 0.18
    FINGER_EXTEND_THRESHOLD = 0.04

    def __init__(self, smoothing_window=5, confidence_threshold=0.7, min_hold_frames=3):
        self.smoothing_window = smoothing_window
        self.confidence_threshold = confidence_threshold
        self.min_hold_frames = min_hold_frames
        self.gesture_buffer = deque(maxlen=smoothing_window)
        self.current_gesture = "None"

    def _palm_scale(self, landmarks) -> float:
        wrist = landmarks[0]
        middle_mcp = landmarks[9]
        scale = math.hypot(middle_mcp.x - wrist.x, middle_mcp.y - wrist.y)
        return max(scale, 0.08)

    def _is_finger_extended(self, landmarks, finger_idx, handedness="Right") -> bool:
        scale = self._palm_scale(landmarks)

        if finger_idx == 0:
            tip = landmarks[FINGER_TIPS[0]]
            ip = landmarks[THUMB_IP]
            side_delta = (tip.x - ip.x) / scale
            if handedness == "Left":
                return side_delta < -self.THUMB_SIDE_THRESHOLD
            return side_delta > self.THUMB_SIDE_THRESHOLD

        tip_y = landmarks[FINGER_TIPS[finger_idx]].y
        pip_y = landmarks[FINGER_PIPS[finger_idx]].y
        mcp_y = landmarks[FINGER_MCPS[finger_idx]].y
        extend_ratio = (pip_y - tip_y) / scale
        return tip_y < pip_y and pip_y < mcp_y and extend_ratio > self.FINGER_EXTEND_THRESHOLD

    def _count_extended_fingers(self, landmarks, handedness="Right") -> int:
        return sum(
            self._is_finger_extended(landmarks, i, handedness)
            for i in range(5)
        )

    def _others_folded(self, landmarks, handedness, exclude=frozenset()) -> bool:
        for i in range(1, 5):
            if i in exclude:
                continue
            if self._is_finger_extended(landmarks, i, handedness):
                return False
        return True

    def _is_thumbs_up(self, landmarks, handedness) -> bool:
        scale = self._palm_scale(landmarks)
        thumb_tip = landmarks[FINGER_TIPS[0]]
        thumb_mcp = landmarks[FINGER_MCPS[0]]
        if (thumb_mcp.y - thumb_tip.y) / scale < 0.12:
            return False
        return self._others_folded(landmarks, handedness)

    def _is_thumbs_down(self, landmarks, handedness) -> bool:
        scale = self._palm_scale(landmarks)
        thumb_tip = landmarks[FINGER_TIPS[0]]
        thumb_mcp = landmarks[FINGER_MCPS[0]]
        if (thumb_tip.y - thumb_mcp.y) / scale < 0.12:
            return False
        return self._others_folded(landmarks, handedness)

    def _is_ok_sign(self, landmarks, handedness) -> bool:
        scale = self._palm_scale(landmarks)
        thumb_tip = landmarks[FINGER_TIPS[0]]
        index_tip = landmarks[FINGER_TIPS[1]]
        ring_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y) / scale
        if ring_dist > 0.35:
            return False
        return (
            self._is_finger_extended(landmarks, 2, handedness)
            and self._is_finger_extended(landmarks, 3, handedness)
            and self._is_finger_extended(landmarks, 4, handedness)
        )

    def _is_rock(self, landmarks, handedness) -> bool:
        return (
            self._is_finger_extended(landmarks, 1, handedness)
            and self._is_finger_extended(landmarks, 4, handedness)
            and not self._is_finger_extended(landmarks, 0, handedness)
            and not self._is_finger_extended(landmarks, 2, handedness)
            and not self._is_finger_extended(landmarks, 3, handedness)
        )

    def classify(self, landmarks, handedness="Right"):
        """
        Классификация жеста. Сложные жесты проверяются до простого подсчёта пальцев.
        """
        if self._is_thumbs_up(landmarks, handedness):
            return "ThumbsUp", 0.92
        if self._is_thumbs_down(landmarks, handedness):
            return "ThumbsDown", 0.92
        if self._is_ok_sign(landmarks, handedness):
            return "OK", 0.9
        if self._is_rock(landmarks, handedness):
            return "Rock", 0.88

        extended_count = self._count_extended_fingers(landmarks, handedness)
        gesture = "None"
        confidence = 0.5

        if extended_count == 0:
            gesture, confidence = "Fist", 0.85
        elif extended_count == 1:
            if self._is_finger_extended(landmarks, 1, handedness):
                gesture, confidence = "One", 0.88
            elif self._is_finger_extended(landmarks, 4, handedness):
                gesture, confidence = "Pinky", 0.78
        elif extended_count == 2:
            if (
                self._is_finger_extended(landmarks, 1, handedness)
                and self._is_finger_extended(landmarks, 2, handedness)
            ):
                gesture, confidence = "Peace", 0.92
            elif (
                self._is_finger_extended(landmarks, 0, handedness)
                and self._is_finger_extended(landmarks, 4, handedness)
            ):
                gesture, confidence = "Shaka", 0.85
        elif extended_count == 3:
            if all(self._is_finger_extended(landmarks, i, handedness) for i in (1, 2, 3)):
                gesture, confidence = "Three", 0.88
        elif extended_count == 4:
            gesture, confidence = "Four", 0.88
        elif extended_count == 5:
            gesture, confidence = "Open", 0.92

        return gesture, confidence

    def get_stable_gesture(self, landmarks, handedness="Right") -> str:
        gesture, confidence = self.classify(landmarks, handedness)

        if confidence >= self.confidence_threshold:
            self.gesture_buffer.append(gesture)

        if len(self.gesture_buffer) > 0:
            gestures = list(self.gesture_buffer)
            most_common = max(set(gestures), key=gestures.count)
            if gestures.count(most_common) >= self.min_hold_frames:
                self.current_gesture = most_common

        return self.current_gesture

    def reset(self) -> None:
        self.gesture_buffer.clear()
        self.current_gesture = "None"


def initialize_detector(model_asset_path='hand_landmarker.task'):
    """Инициализация детектора рук MediaPipe."""
    base_options = python.BaseOptions(model_asset_path=model_asset_path)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.HandLandmarker.create_from_options(options)


def draw_hand_skeleton(frame, landmarks, h, w):
    """Отрисовка скелета руки."""
    for pt1_idx, pt2_idx in HAND_CONNECTIONS:
        pt1 = landmarks[pt1_idx]
        pt2 = landmarks[pt2_idx]
        cv2.line(
            frame,
            (int(pt1.x * w), int(pt1.y * h)),
            (int(pt2.x * w), int(pt2.y * h)),
            (255, 255, 255), 2,
        )

    for i, lm in enumerate(landmarks):
        color = (0, 255, 0) if i in FINGER_TIPS else (0, 0, 255)
        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 6, color, -1)


def main():
    """Standalone-режим для тестирования распознавания."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Ошибка: не удалось подключиться к веб-камере")
        return

    detector = initialize_detector()
    classifier = GestureClassifier()

    print("Жесты: Fist, One, Peace, Open, ThumbsUp, ThumbsDown, OK, Rock, ...")
    print("Нажмите 'q' для выхода")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            h, w, _ = frame.shape
            detection_result = detector.detect(mp_image)

            if detection_result.hand_landmarks:
                for idx, hand_landmarks in enumerate(detection_result.hand_landmarks):
                    draw_hand_skeleton(frame, hand_landmarks, h, w)
                    handedness = "Right"
                    if detection_result.handedness and idx < len(detection_result.handedness):
                        handedness = detection_result.handedness[idx][0].display_name
                    gesture = classifier.get_stable_gesture(hand_landmarks, handedness)
                    cv2.putText(
                        frame, f"{gesture} ({handedness})",
                        (10, 30 + idx * 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2,
                    )

            cv2.imshow("Hand Gesture Recognition", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        detector.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
