# ML Final Project — Управление презентацией жестами

Приложение распознаёт жесты руки через веб-камеру (MediaPipe Hands) и эмулирует нажатия клавиш для управления презентацией.

## Возможности

- Распознавание жестов в реальном времени
- Настраиваемый маппинг жест → действие через GUI
- Старт/стоп слежения, cooldown, визуальная обратная связь
- Сохранение настроек в `config.json`

## Поддерживаемые жесты

| Жест | Описание |
|---|---|
| One | Указательный палец |
| Fist | Кулак |
| Open | Открытая ладонь |
| Peace | Знак мира (V) |
| Pinky | Мизинец |
| Shaka | Большой + мизинец |
| Three | Три пальца |
| Four | Четыре пальца |
| ThumbsUp | Большой палец вверх |
| ThumbsDown | Большой палец вниз |
| OK | Жест «OK» (кольцо) |
| Rock | Рок (указательный + мизинец) |

По умолчанию привязаны только One, Fist, Open, Peace. Остальные жесты доступны для настройки в GUI.

## Действия

| Действие | Клавиша |
|---|---|
| Следующий слайд | → |
| Предыдущий слайд | ← |
| Запуск презентации | F5 |
| Завершение презентации | Esc |

## Требования

- Windows 10+
- Python 3.10+ (для запуска из исходников)
- Веб-камера
- Файл модели `hand_landmarker.task` в корне проекта

## Запуск из исходников

```bash
# Клонировать репозиторий, скачать модель (если ещё не скачана)
curl -O https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task

# Установить зависимости
pip install -r requirements.txt

# Запустить
cd code
python main.py
```

Откроются два окна: панель настроек (tkinter) и видео с камеры (OpenCV).

## Сборка .exe (Windows)

```bash
cd code
build.bat
```

Или вручную:

```bash
pip install pyinstaller
cd code
pyinstaller GesturePresentation.spec --noconfirm
```

Результат: `code/dist/GesturePresentation.exe`

При первом запуске exe создаст `config.json` рядом с собой. Модель MediaPipe встроена в exe.

## Структура проекта

```
ML_final_project/
├── config.json              # Настройки (маппинг, параметры)
├── hand_landmarker.task     # Модель MediaPipe
├── requirements.txt
└── code/
    ├── main.py              # Точка входа
    ├── config_manager.py    # Загрузка/сохранение config
    ├── gesture_controller.py
    ├── AI/
    │   └── gesture_recognition.py
    ├── UI/
    │   ├── settings_gui.py
    │   └── presentation_controller.py
    ├── GesturePresentation.spec
    └── build.bat
```

## Параметры config.json

| Параметр | Описание | По умолчанию |
|---|---|---|
| gesture_mapping | Жест → действие | One/Fist/Open/Peace |
| cooldown_seconds | Блокировка повтора (сек) | 5.0 |
| smoothing_window | Окно сглаживания (кадры) | 5 |
| confidence_threshold | Порог уверенности | 0.7 |
| min_hold_frames | Мин. кадров удержания жеста | 3 |
| camera_index | Индекс камеры | 0 |
