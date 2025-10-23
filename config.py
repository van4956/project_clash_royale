# -*- coding: utf-8 -*-
"""
Конфигурационный файл проекта Clash Royale Bot
Содержит все основные настройки и константы
"""

import os


# ===== ПУТИ К ФАЙЛАМ И ПАПКАМ =====
# Путь к папке с обученной моделью YOLO
MODEL_PATH = os.path.join("models", "train_clash_royale_test5", "weights", "best.pt")
# Путь к файлу для сохранения координат выбранной области экрана
ROI_CONFIG_PATH = "roi_config.txt"


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ROI =====
def get_roi_bounds():
    """
    Читает границы ROI из файла roi_config.txt.

    Returns:
        tuple: (x_min, y_min, x_max, y_max) - границы ROI области
               или (0, 0, 1920, 1080) по умолчанию если файл не найден

    Формат файла: "top,left,width,height"
    Пример: "100,1120,960,1700"
    """
    try:
        if os.path.exists(ROI_CONFIG_PATH):
            with open(ROI_CONFIG_PATH, 'r', encoding='utf-8') as f:
                coords = f.read().strip().split(',')
                top = int(coords[0])      # y_min
                left = int(coords[1])     # x_min
                width = int(coords[2])
                height = int(coords[3])

                x_min = left
                y_min = top
                x_max = left + width
                y_max = top + height

                return (x_min, y_min, x_max, y_max)
        else:
            # Значения по умолчанию (полный экран Full HD)
            return (0, 0, 1920, 1080)
    except Exception as e:
        print(f"Ошибка при чтении ROI: {e}")
        # Возвращаем безопасные значения по умолчанию
        return (0, 0, 1920, 1080)


# ===== НАСТРОЙКИ ЗАХВАТА ЭКРАНА =====
# Количество кадров в секунду для обработки
# FPS = 0.25 → 1 кадр в 4 секунды (для тестирования)
# FPS = 0.5 → 1 кадр в 2 секунды (для тестирования)
# FPS = 4.0 → 4 кадра в секунду (рабочий режим после тестирования)
FPS = 1


# ===== НАСТРОЙКИ ДЛЯ YOLO ДЕТЕКЦИИ =====
# Минимальный порог уверенности для детекции объектов
YOLO_CONFIDENCE = 0.42
# Размер изображения для обработки моделью (ширина, высота)
YOLO_IMG_SIZE = 640
# Минимальный порог IoU для фильтрации задвоенных детекций
YOLO_IOU = 0.85


# ===== НАСТРОЙКИ ОТЛАДКИ/ТЕСТИРОВАНИЯ =====
# Флаг для сохранения обработанных кадров с детекциями (для отладки)
DETECTION_TEST = True  # True - сохранять кадры, False - не сохранять
# Папка для сохранения обработанных кадров
DETECTION_OUTPUT_DIR = "detection"


# ===== НАСТРОЙКИ ДЛЯ СОХРАНЕННЫХ ИЗОБРАЖЕНИЙ =====
# Цвет рамки при выборе области экрана (BGR формат для OpenCV)
SELECTION_COLOR = (64, 64, 64)  # Темно серый
# Толщина линии рамки при выборе области
SELECTION_THICKNESS = 2


# ===== ТЕКСТОВЫЕ СООБЩЕНИЯ =====
# Сообщения для пользователя на русском языке
MSG_SELECT_AREA = "Выделите область игры мышью и нажмите Enter. ESC для отмены."
MSG_AREA_SAVED = "Область сохранена: x={}, y={}, width={}, height={}"
MSG_AREA_LOADED = "Координаты области загружены из файла"
MSG_STARTING_CAPTURE = "Запуск захвата экрана..."
MSG_DETECTION_RESULT = "[{timestamp}] Обнаружено объектов: {count}"
MSG_OBJECT_DETECTED = "  - {class_name} (conf: {confidence:.2f})"
MSG_NO_MODEL = "ОШИБКА: Модель не найдена по пути: {}"
MSG_PRESS_Q_TO_QUIT = "Нажмите 'Ctrl+C' в терминале для остановки программы"


# ===== НАСТРОЙКИ OVERLAY =====
# Доска (фоновая панель)
BOARD_WIDTH_PERCENT = 0.8  # ширина доски в % от ширины ROI
BOARD_HEIGHT_PERCENT = 0.085  # высота доски в % от высоты ROI
BOARD_COLOR = (240, 76, 76)  # цвет доски
BOARD_ALPHA = 0.5  # прозрачность доски

# Отступ и размер капельки эликсира
ELIXIR_DROP_INDENT_PERCENT = 0.01  # отступ в % от ширины ROI
ELIXIR_DROP_SIZE_PERCENT = 0.05  # размер капельки в % от ширины ROI

# Шкала эликсира
ELIXIR_BAR_WIDTH_PERCENT = 0.7  # ширина шкалы в % от ширины ROI
ELIXIR_BAR_HEIGHT_RATIO = 0.6  # высота шкалы в % от высоты капельки
ELIXIR_BAR_OFFSET_RATIO = 0.2  # отступ от капельки в % от высоты капельки

# Карты (визуализация цикла карт)
CARD_SCALE = 0.2  # коэффициент масштабирования карт (калибруется визуально)

# Логика подсчета эликсира
ELIXIR_START_BALANCE = 6.5  # стартовый запас эликсира
ELIXIR_SPEED = 0.33  # скорость прироста (эликсир/сек)
ELIXIR_MAX = 10  # максимальное количество эликсира
