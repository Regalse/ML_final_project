"""
GUI настроек и управления (Этап 4, TASK-4.2–4.4).

Стек: tkinter (встроен в Python, без дополнительных зависимостей).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Optional

from config_manager import (
    ACTION_LABELS,
    AVAILABLE_ACTIONS,
    AVAILABLE_GESTURES,
    ConfigManager,
)


class SettingsGUI:
    """Окно настроек с визуальной обратной связью и управлением слежением."""

    def __init__(
        self,
        config_manager: ConfigManager,
        on_apply: Callable[[Dict], None],
        on_toggle_tracking: Callable[[bool], None],
        on_close: Callable[[], None],
    ):
        self.config_manager = config_manager
        self.on_apply = on_apply
        self.on_toggle_tracking = on_toggle_tracking
        self.on_close = on_close

        self.tracking_active = False
        self._gesture_vars: Dict[str, tk.StringVar] = {}

        self.root = tk.Tk()
        self.root.title("Управление презентацией жестами")
        self.root.geometry("520x780")
        self.root.minsize(480, 700)
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)

        self._build_ui()
        self._load_from_config()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # --- Статус (TASK-4.3) ---
        status_frame = ttk.LabelFrame(main, text="Статус", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.tracking_label = ttk.Label(status_frame, text="Слежение: остановлено", font=("Segoe UI", 11, "bold"))
        self.tracking_label.pack(anchor=tk.W)

        self.gesture_label = ttk.Label(status_frame, text="Жест: —", font=("Segoe UI", 10))
        self.gesture_label.pack(anchor=tk.W, pady=(6, 0))

        self.action_label = ttk.Label(status_frame, text="Действие: —", font=("Segoe UI", 10))
        self.action_label.pack(anchor=tk.W, pady=(4, 0))

        self.message_label = ttk.Label(status_frame, text="Сообщение: ожидание запуска", foreground="#555")
        self.message_label.pack(anchor=tk.W, pady=(4, 0))

        # --- Старт/Стоп (TASK-4.4) ---
        control_frame = ttk.Frame(main)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        self.toggle_btn = ttk.Button(control_frame, text="▶ Старт слежения", command=self._toggle_tracking)
        self.toggle_btn.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(control_frame, text="Сброс состояний", command=self._reset_states).pack(side=tk.LEFT)

        # --- Маппинг жестов (прокручиваемый список) ---
        mapping_frame = ttk.LabelFrame(main, text="Привязка жестов к действиям", padding=10)
        mapping_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        canvas = tk.Canvas(mapping_frame, highlightthickness=0, height=280)
        scrollbar = ttk.Scrollbar(mapping_frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_inner = ttk.Frame(canvas)

        scroll_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        action_values = [f"{ACTION_LABELS[a]} ({a})" for a in AVAILABLE_ACTIONS]

        for i, gesture in enumerate(AVAILABLE_GESTURES):
            ttk.Label(scroll_inner, text=gesture, width=12).grid(row=i, column=0, sticky=tk.W, pady=3)

            var = tk.StringVar()
            combo = ttk.Combobox(
                scroll_inner,
                textvariable=var,
                values=action_values,
                state="readonly",
                width=34,
            )
            combo.grid(row=i, column=1, sticky=tk.EW, padx=(8, 0), pady=3)
            self._gesture_vars[gesture] = var

        scroll_inner.columnconfigure(1, weight=1)

        # --- Параметры ---
        params_frame = ttk.LabelFrame(main, text="Параметры", padding=10)
        params_frame.pack(fill=tk.X, pady=(0, 10))

        self.cooldown_var = tk.DoubleVar(value=5.0)
        self._add_spinbox_row(params_frame, "Cooldown (сек):", self.cooldown_var, 0.5, 30.0, 0.5, 0)

        self.smoothing_var = tk.IntVar(value=5)
        self._add_spinbox_row(params_frame, "Сглаживание (кадры):", self.smoothing_var, 1, 20, 1, 1)

        self.confidence_var = tk.DoubleVar(value=0.7)
        self._add_spinbox_row(params_frame, "Порог уверенности:", self.confidence_var, 0.1, 1.0, 0.05, 2)

        self.min_hold_var = tk.IntVar(value=3)
        self._add_spinbox_row(params_frame, "Мин. кадров удержания:", self.min_hold_var, 1, 10, 1, 3)

        # --- Кнопки ---
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Применить", command=self._apply_settings).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Сохранить в config.json", command=self._save_config).pack(side=tk.LEFT)

    def _add_spinbox_row(self, parent, label, variable, from_, to, increment, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        ttk.Spinbox(
            parent,
            textvariable=variable,
            from_=from_,
            to=to,
            increment=increment,
            width=10,
        ).grid(row=row, column=1, sticky=tk.W, padx=(8, 0), pady=4)

    def _action_to_display(self, action: str) -> str:
        return f"{ACTION_LABELS.get(action, action)} ({action})"

    def _display_to_action(self, display: str) -> str:
        if display.endswith(")"):
            return display.rsplit("(", 1)[-1][:-1]
        return display

    def _load_from_config(self) -> None:
        cfg = self.config_manager.config
        mapping = cfg.get("gesture_mapping", {})

        for gesture, var in self._gesture_vars.items():
            action = mapping.get(gesture, "none")
            var.set(self._action_to_display(action))

        self.cooldown_var.set(cfg.get("cooldown_seconds", 5.0))
        self.smoothing_var.set(cfg.get("smoothing_window", 5))
        self.confidence_var.set(cfg.get("confidence_threshold", 0.7))
        self.min_hold_var.set(cfg.get("min_hold_frames", 3))

    def _collect_config(self) -> Dict:
        gesture_mapping = {}
        for gesture, var in self._gesture_vars.items():
            action = self._display_to_action(var.get())
            if action != "none":
                gesture_mapping[gesture] = action

        return {
            "gesture_mapping": gesture_mapping,
            "cooldown_seconds": self.cooldown_var.get(),
            "smoothing_window": self.smoothing_var.get(),
            "confidence_threshold": self.confidence_var.get(),
            "min_hold_frames": self.min_hold_var.get(),
            "camera_index": self.config_manager.config.get("camera_index", 0),
        }

    def _apply_settings(self) -> None:
        new_config = self._collect_config()
        self.on_apply(new_config)
        messagebox.showinfo("Настройки", "Настройки применены.")

    def _save_config(self) -> None:
        new_config = self._collect_config()
        self.config_manager.update(new_config)
        self.on_apply(new_config)
        messagebox.showinfo("Сохранение", f"Настройки сохранены в:\n{self.config_manager.config_path}")

    def _toggle_tracking(self) -> None:
        self.tracking_active = not self.tracking_active
        self.on_toggle_tracking(self.tracking_active)

        if self.tracking_active:
            self.toggle_btn.config(text="⏹ Стоп слежения")
            self.tracking_label.config(text="Слежение: активно", foreground="#1a7f37")
        else:
            self.toggle_btn.config(text="▶ Старт слежения")
            self.tracking_label.config(text="Слежение: остановлено", foreground="#333")
            self.action_label.config(text="Действие: —")
            self.message_label.config(text="Сообщение: слежение остановлено")

    def _reset_states(self) -> None:
        self.on_apply({"reset_states": True})

    def update_status(self, gesture: str, result: Dict, status: Dict) -> None:
        """Обновление визуальной обратной связи (TASK-4.3)."""
        self.gesture_label.config(text=f"Жест: {gesture}")

        if not self.tracking_active:
            return

        if result.get("triggered"):
            action = result.get("action", "—")
            label = ACTION_LABELS.get(action, action)
            self.action_label.config(text=f"Действие: {label}", foreground="#1a7f37")
            self.message_label.config(text=f"Сообщение: {result.get('message', '')}", foreground="#1a7f37")
        elif result.get("blocked"):
            self.action_label.config(text="Действие: заблокировано (cooldown)", foreground="#b54708")
            remaining = result.get("cooldown_remaining", 0)
            self.message_label.config(
                text=f"Сообщение: повтор через {remaining:.1f} сек",
                foreground="#b54708",
            )
        else:
            self.action_label.config(text="Действие: —", foreground="#333")
            self.message_label.config(
                text=f"Сообщение: {result.get('message', 'ожидание жеста')}",
                foreground="#555",
            )

    def run(self) -> None:
        self.root.mainloop()

    def schedule(self, callback: Callable, interval_ms: int = 100) -> None:
        self.root.after(interval_ms, callback)

    def _handle_close(self) -> None:
        self.on_close()
        self.root.destroy()
