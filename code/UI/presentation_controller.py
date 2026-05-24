"""
Модуль управления презентацией (Presentation Controller)
Использует библиотеку pynput для эмуляции нажатий клавиш.

TASK-2.1: Выбор и интеграция библиотеки эмуляции
TASK-2.2: Маппинг действий на клавиши
TASK-2.3: Тестирование эмуляции
"""

from pynput.keyboard import Key, Controller


class PresentationController:
    """
    Контроллер для управления презентацией через эмуляцию клавиатуры.
    
    Маппинг действий:
    - next_slide: Стрелка вправо / Page Down / Пробел
    - prev_slide: Стрелка влево / Page Up
    - start_presentation: F5
    """
    
    def __init__(self):
        """Инициализация контроллера клавиатуры."""
        self.keyboard = Controller()
    
    def next_slide(self):
        """
        Перейти к следующему слайду.
        Эмулирует нажатие стрелки вправо (Right Arrow).
        """
        self.keyboard.press(Key.right)
        self.keyboard.release(Key.right)
        print("[PresentationController] Next slide")
    
    def prev_slide(self):
        """
        Перейти к предыдущему слайду.
        Эмулирует нажатие стрелки влево (Left Arrow).
        """
        self.keyboard.press(Key.left)
        self.keyboard.release(Key.left)
        print("[PresentationController] Previous slide")
    
    def start_presentation(self):
        """
        Запустить презентацию с начала.
        Эмулирует нажатие F5.
        """
        self.keyboard.press(Key.f5)
        self.keyboard.release(Key.f5)
        print("[PresentationController] Start presentation (F5)")
    
    def end_presentation(self):
        """
        Завершить презентацию.
        Эмулирует нажатие Escape.
        """
        self.keyboard.press(Key.esc)
        self.keyboard.release(Key.esc)
        print("[PresentationController] End presentation (Esc)")


# Пример использования и инструкция по ручному тестированию
if __name__ == "__main__":
    print("=" * 60)
    print("Presentation Controller - Ручное тестирование")
    print("=" * 60)
    print()
    print("ИНСТРУКЦИЯ ПО ТЕСТИРОВАНИЮ:")
    print("-" * 60)
    print("1. Откройте любую программу для презентаций:")
    print("   - Microsoft PowerPoint")
    print("   - Google Slides")
    print("   - LibreOffice Impress")
    print()
    print("2. Быстро переключитесь на окно презентации (Alt+Tab)")
    print()
    print("3. Запустите этот скрипт. Он выполнит следующие действия:")
    print("   a) Запуск презентации (F5)")
    print("   b) Пауза 2 секунды")
    print("   c) Следующий слайд (Right Arrow) x3")
    print("   d) Предыдущий слайд (Left Arrow) x1")
    print("   e) Пауза 2 секунды")
    print("   f) Завершение презентации (Esc)")
    print()
    print("4. Наблюдайте за реакцией презентации.")
    print("-" * 60)
    print()
    
    import time
    
    controller = PresentationController()
    
    print("Запуск тестовой последовательности через 3 секунды...")
    print("Успейте переключиться на окно презентации!")
    time.sleep(3)
    
    # Тест: Запуск презентации
    print("\n>>> Тест: Запуск презентации (F5)")
    controller.start_presentation()
    time.sleep(2)
    
    # Тест: Переход вперед
    print("\n>>> Тест: Следующий слайд x3")
    for i in range(3):
        controller.next_slide()
        time.sleep(1)
    
    # Тест: Переход назад
    print("\n>>> Тест: Предыдущий слайд x1")
    controller.prev_slide()
    time.sleep(1)
    
    # Тест: Завершение
    print("\n>>> Тест: Завершение презентации (Esc)")
    controller.end_presentation()
    
    print("\n" + "=" * 60)
    print("Тестирование завершено!")
    print("=" * 60)
