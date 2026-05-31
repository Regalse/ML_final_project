"""
Основной модуль системы управления презентацией жестами.
Интегрирует распознавание жестов (AI), управление презентацией (UI) и GUI настроек.

Запуск: python main.py
"""

import sys
import os
import threading
import time
from collections import deque

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'UI'))

import cv2
import mediapipe as mp

from AI.gesture_recognition import GestureClassifier, draw_hand_skeleton, initialize_detector
from UI.presentation_controller import PresentationController
from UI.settings_gui import SettingsGUI
from config_manager import ConfigManager, get_resource_path
from gesture_controller import GestureController


class GesturePresentationSystem:
    """Система управления презентацией жестами с конфигурацией и GUI."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        cfg = config_manager.config

        self.presentation_controller = PresentationController()
        self.gesture_controller = GestureController(
            self.presentation_controller,
            gesture_mapping=config_manager.get_gesture_mapping(),
            cooldown_seconds=cfg["cooldown_seconds"],
        )
        self.classifier = GestureClassifier(
            smoothing_window=cfg["smoothing_window"],
            confidence_threshold=cfg["confidence_threshold"],
            min_hold_frames=cfg.get("min_hold_frames", 3),
        )

        model_path = get_resource_path("hand_landmarker.task")
        self.detector = initialize_detector(model_path)

        self._cleaned = False
        self.cap = cv2.VideoCapture(cfg["camera_index"])
        if not self.cap.isOpened():
            raise RuntimeError("Ошибка: не удалось подключиться к веб-камере")

        self.frame_count = 0
        self.fps = 0
        self.last_fps_time = None

        self._running = False
        self._video_thread: threading.Thread | None = None
        self._latest_gesture = "None"
        self._latest_result = {'triggered': False, 'blocked': False, 'cooldown_remaining': 0, 'action': None, 'message': ''}
        self._latest_status = self.gesture_controller.get_status()
        self._status_lock = threading.Lock()
        self.gui: SettingsGUI | None = None

    def apply_config(self, new_config: dict) -> None:
        if new_config.get("reset_states"):
            self.gesture_controller.reset()
            self.classifier.reset()
            return

        mapping = {
            k: v for k, v in new_config.get("gesture_mapping", {}).items()
            if v and v != "none"
        }
        self.gesture_controller.update_mapping(mapping)
        self.gesture_controller.set_cooldown(float(new_config.get("cooldown_seconds", 5.0)))

        self.classifier.smoothing_window = int(new_config.get("smoothing_window", 5))
        self.classifier.confidence_threshold = float(new_config.get("confidence_threshold", 0.7))
        self.classifier.min_hold_frames = int(new_config.get("min_hold_frames", 3))
        self.classifier.gesture_buffer = deque(maxlen=self.classifier.smoothing_window)

    def set_tracking(self, enabled: bool) -> None:
        self.gesture_controller.set_enabled(enabled)

    def start_video_loop(self) -> None:
        self._running = True
        self._video_thread = threading.Thread(target=self._video_loop, daemon=True)
        self._video_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._video_thread and self._video_thread.is_alive():
            self._video_thread.join(timeout=2.0)
        self.cleanup()

    def _video_loop(self) -> None:
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                break

            self._calculate_fps()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            h, w, _ = frame.shape

            detection_result = self.detector.detect(mp_image)
            gesture = "None"
            result = {
                'triggered': False, 'blocked': False,
                'cooldown_remaining': 0, 'action': None, 'message': '',
            }

            if detection_result.hand_landmarks:
                for idx, hand_landmarks in enumerate(detection_result.hand_landmarks):
                    draw_hand_skeleton(frame, hand_landmarks, h, w)

                    handedness = "Right"
                    if detection_result.handedness and idx < len(detection_result.handedness):
                        handedness = detection_result.handedness[idx][0].display_name

                    gesture = self.classifier.get_stable_gesture(hand_landmarks, handedness)
                    result = self.gesture_controller.process_gesture(gesture)

                    label = f"{gesture} ({handedness})"
                    cv2.putText(frame, label, (10, 30 + idx * 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                result = self.gesture_controller.process_gesture("None")

            status = self.gesture_controller.get_status()
            self._draw_ui_overlay(frame, gesture, result, status)

            with self._status_lock:
                self._latest_gesture = gesture
                self._latest_result = result
                self._latest_status = status

            cv2.imshow("Gesture Presentation Control", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self._running = False
                if self.gui:
                    self.gui.root.after(0, self.gui.root.quit)
                break

        self.cleanup()

    def poll_gui_status(self) -> None:
        if not self.gui or not self._running:
            return

        with self._status_lock:
            gesture = self._latest_gesture
            result = dict(self._latest_result)
            status = self._latest_status

        self.gui.update_status(gesture, result, status)
        self.gui.schedule(self.poll_gui_status, 100)

    def _calculate_fps(self) -> None:
        current_time = time.time()
        if self.last_fps_time is not None:
            elapsed = current_time - self.last_fps_time
            if elapsed > 0:
                self.fps = self.frame_count / elapsed

        if self.last_fps_time is None or (current_time - self.last_fps_time >= 1.0):
            self.last_fps_time = current_time
            self.frame_count = 0

        self.frame_count += 1

    def _draw_ui_overlay(self, frame, gesture, result, status):
        h, w, _ = frame.shape
        info_y = 10
        line_height = 25

        tracking_text = "TRACKING: ON" if self.gesture_controller.enabled else "TRACKING: OFF"
        tracking_color = (0, 255, 0) if self.gesture_controller.enabled else (128, 128, 128)
        cv2.putText(frame, tracking_text, (10, info_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, tracking_color, 2)
        info_y += line_height

        gesture_color = (0, 255, 0) if result['triggered'] else (0, 255, 255) if result['blocked'] else (255, 255, 255)
        cv2.putText(frame, f"Gesture: {gesture}", (10, info_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, gesture_color, 2)
        info_y += line_height

        if result['triggered']:
            cv2.putText(frame, f"ACTION: {result['action'].upper()}", (10, info_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        elif result['blocked']:
            cv2.putText(frame, f"BLOCKED ({result['cooldown_remaining']:.1f}s)", (10, info_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        info_y += line_height * 2

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

        cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

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

    def cleanup(self) -> None:
        if getattr(self, '_cleaned', False):
            return
        self._cleaned = True
        self.cap.release()
        self.detector.close()
        cv2.destroyAllWindows()


def main():
    try:
        config_manager = ConfigManager()
        system = GesturePresentationSystem(config_manager)

        def on_apply(new_config):
            system.apply_config(new_config)

        def on_toggle(enabled):
            system.set_tracking(enabled)

        def on_close():
            system.stop()

        gui = SettingsGUI(
            config_manager=config_manager,
            on_apply=on_apply,
            on_toggle_tracking=on_toggle,
            on_close=on_close,
        )
        system.gui = gui

        system.start_video_loop()
        gui.schedule(system.poll_gui_status, 100)
        gui.run()

        system.stop()

    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
