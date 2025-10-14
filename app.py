# -*- coding: utf-8 -*-
"""
Главный файл приложения Clash Royale Bot
Точка входа в программу - запускается пользователем для старта бота
"""

import time
from datetime import datetime  # Для вывода временных меток
import os
import cv2  # OpenCV для сохранения изображений

# Импорт наших модулей
from modules.screen_capture import ScreenCapture  # Модуль захвата экрана
from modules.detector import CardDetector  # Модуль детекции карт через YOLO
from modules.overlay_static import StaticOverlay  # Статичные overlay элементы (доска, капелька)
from modules.overlay_dynamic import DynamicOverlay  # Динамический overlay (шкала, цифра, карты)

# Импорт конфигурации
from config import (
    FPS,                        # Частота обработки кадров
    MSG_STARTING_CAPTURE,       # Сообщение о начале захвата
    MSG_DETECTION_RESULT,       # Шаблон сообщения о результатах детекции
    MSG_OBJECT_DETECTED,        # Шаблон сообщения об обнаруженном объекте
    MSG_PRESS_Q_TO_QUIT,        # Инструкция для пользователя
    DETECTION_TEST,             # Флаг сохранения кадров для отладки
    DETECTION_OUTPUT_DIR,       # Папка для сохранения кадров
    BOARD_WIDTH_PERCENT,        # Ширина доски
    BOARD_HEIGHT_PERCENT,       # Высота доски
    BOARD_COLOR,                # Цвет доски
    BOARD_ALPHA,                # Прозрачность доски
    ELIXIR_DROP_INDENT_PERCENT, # Отступ в % от ширины ROI
    ELIXIR_DROP_SIZE_PERCENT,   # Размер капельки в % от ширины ROI
    ELIXIR_BAR_WIDTH_PERCENT,   # Ширина шкалы эликсира
    ELIXIR_BAR_HEIGHT_RATIO,    # Высота шкалы относительно капельки
    ELIXIR_BAR_OFFSET_RATIO,    # Отступ шкалы от капельки
    ELIXIR_START_BALANCE,       # Стартовый эликсир
    ELIXIR_SPEED,               # Скорость накопления эликсира
    ELIXIR_MAX                  # Максимум эликсира
)


def main():
    """
    Главная функция приложения

    Последовательность работы:
    1. Инициализация модулей (захват экрана, детектор)
    2. Выбор области экрана (ROI)
    3. Создание статичного overlay (доска, капелька)
    4. Загрузка модели YOLO
    5. Основной цикл: захват кадров → детекция → вывод результата в терминал и динамического overlay
    6. Очистка ресурсов при завершении
    """

    print("=" * 60)
    print("Clash Royale Bot - Система детекции карт")
    print("=" * 60)
    print()


    # ===== ШАГ 1: ИНИЦИАЛИЗАЦИЯ МОДУЛЕЙ =====
    print("-> Инициализация модулей...")

    # Создаем объект для захвата экрана
    screen_capture = ScreenCapture()

    # Создаем объект детектора карт
    detector = CardDetector()

    print("✓ Модули инициализированы")
    print()


    # ===== ШАГ 2: ВЫБОР ОБЛАСТИ ЭКРАНА =====
    print("-> Настройка области экрана...")

    # Пытаемся загрузить сохраненные координаты из файла
    if not screen_capture.load_roi():
        # Если файл не найден, запускаем интерактивный выбор области
        print("Сохраненные координаты не найдены!")
        print("Запуск режима выбора области экрана...")

        roi = screen_capture.select_roi()

        # Если пользователь отменил выбор (нажал ESC), завершаем программу
        if roi is None:
            print("Программа завершена пользователем.")
            return

    print("✓ Область экрана настроена")
    print()


    # ===== ШАГ 3: СОЗДАНИЕ OVERLAY ЭЛЕМЕНТОВ =====
    print("-> Создание статичного overlay...")

    # Проверяем что ROI установлен
    if screen_capture.roi is None:
        print("ОШИБКА: ROI не установлен. Завершение программы.")
        return

    # Вычисляем параметры относительно размера ROI
    roi_width = screen_capture.roi['width']
    roi_height = screen_capture.roi['height']

    # === ПАРАМЕТРЫ ДЛЯ ДОСКИ ===
    board_width = int(roi_width * BOARD_WIDTH_PERCENT)
    board_height = int(roi_height * BOARD_HEIGHT_PERCENT)
    board_x = screen_capture.roi['left']
    board_y = screen_capture.roi['top']

    # === ПАРАМЕТРЫ ДЛЯ КАПЕЛЬКИ ===
    drop_indent_percent = int(roi_width * ELIXIR_DROP_INDENT_PERCENT)
    drop_x = screen_capture.roi['left'] + drop_indent_percent
    drop_y = screen_capture.roi['top'] + drop_indent_percent
    drop_width = int(roi_width * ELIXIR_DROP_SIZE_PERCENT)

    # === СОЗДАЕМ СТАТИЧНЫЙ OVERLAY (доска + капелька) ===
    drop_image_path = os.path.join("data", "drop_elixir.png")
    overlay_static = StaticOverlay(
        drop_image_path, drop_x, drop_y, drop_width,
        board_x, board_y, board_width, board_height, BOARD_ALPHA, BOARD_COLOR
    )

    if not overlay_static.create_windows():
        print("⚠ Не удалось создать статичный overlay (продолжаем без него)")
        overlay_static = None
    else:
        # Небольшая задержка для правильного отображения
        time.sleep(0.05)
        print("-> Создание динамического overlay...")
        # Получаем реальные размеры капельки после масштабирования
        drop_height = overlay_static.height

        # === ПАРАМЕТРЫ ДЛЯ ШКАЛЫ ===
        # Высота, ширина
        bar_width = int(roi_width * ELIXIR_BAR_WIDTH_PERCENT)
        bar_height = int(drop_height * ELIXIR_BAR_HEIGHT_RATIO)

        # Позиция шкалы (справа от капельки, центрирована вертикально)
        bar_x = drop_x + drop_width + int(drop_height * ELIXIR_BAR_OFFSET_RATIO)
        bar_y = drop_y # + (drop_height - bar_height) // 2

        # === СОЗДАЕМ ДИНАМИЧНЫЙ OVERLAY (шкала, цифра) ===
        overlay_dynamic = DynamicOverlay(
            bar_x, bar_y, bar_width, bar_height,
            drop_x, drop_y, drop_width, drop_height
        )

        if not overlay_dynamic.create_window():
            print("⚠ Не удалось создать динамический overlay")
            overlay_dynamic = None

    print()


    # ===== ШАГ 4: ЗАГРУЗКА МОДЕЛИ YOLO =====
    print("-> Загрузка модели YOLO...")

    # Загружаем обученную модель
    if not detector.load_model():
        # Если загрузка не удалась, завершаем программу
        print("Не удалось загрузить модель. Завершение программы.")
        screen_capture.cleanup()
        return

    print("✓ Модель загружена")
    print()

    # ===== ПОДГОТОВКА ПАПКИ ДЛЯ СОХРАНЕНИЯ КАДРОВ =====
    if DETECTION_TEST:
        # Создаем папку для сохранения кадров если её нет
        if not os.path.exists(DETECTION_OUTPUT_DIR):
            os.makedirs(DETECTION_OUTPUT_DIR)
            print(f"✓ Создана папка для сохранения кадров: {DETECTION_OUTPUT_DIR}")
        else:
            print(f"Режим отладки активен.\nКадры будут сохраняться в папку {DETECTION_OUTPUT_DIR}")
        print()


    # ===== ШАГ 5: ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ =====
    print("=" * 60)
    print(MSG_STARTING_CAPTURE)
    print(f"Частота обработки: {FPS} кадров/сек")
    print(MSG_PRESS_Q_TO_QUIT)
    print("=" * 60)
    print()

    # Вычисляем интервал между кадрами в секундах
    frame_interval = 1.0 / FPS

    # Счетчик обработанных кадров
    frame_count = 0

    # === ИНИЦИАЛИЗАЦИЯ ПОДСЧЕТА ЭЛИКСИРА ===
    elixir_balance = ELIXIR_START_BALANCE  # Текущий запас эликсира
    game_start_time = time.time()  # Время начала накопления эликсира

    try:
        # Бесконечный цикл обработки кадров
        while True:
            # Засекаем время начала обработки кадра
            start_time = time.time()

            # Захватываем текущий кадр из выбранной области экрана
            frame = screen_capture.capture_frame()
            time_after_capture = time.time()

            # Если кадр не получен, пропускаем итерацию
            if frame is None:
                time.sleep(frame_interval)
                continue

            # Отправляем кадр в YOLO модель для детекции карт
            detections = detector.detect(frame)
            time_after_detection = time.time()

            # Вычисляем накопленный эликсир
            game_time_total = time.time() - game_start_time
            elixir_balance = ELIXIR_START_BALANCE + (game_time_total * ELIXIR_SPEED)
            elixir_balance = min(elixir_balance, ELIXIR_MAX)

            # Обновляем динамический overlay (шкала + цифра)
            if overlay_dynamic:
                overlay_dynamic.update_display(elixir_balance)

            # --- СОХРАНЕНИЕ КАДРА С ДЕТЕКЦИЯМИ (если включен режим отладки) ---
            if DETECTION_TEST:
                # Рисуем детекции на кадре (боксы, названия, confidence)
                frame_with_detections = detector.draw_detections(frame, detections)

                # Генерируем имя файла по текущему времени (HH-MM-SS-ms.png)
                current_time = datetime.now()
                filename = current_time.strftime("%H-%M-%S-") + f"{current_time.microsecond // 1000:03d}.png"
                filepath = os.path.join(DETECTION_OUTPUT_DIR, filename)

                # Сохраняем изображение
                cv2.imwrite(filepath, frame_with_detections)
                time_after_save = time.time()

            # --- ВЫВОД РЕЗУЛЬТАТОВ В ТЕРМИНАЛ ---
            # Получаем текущую временную метку
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Увеличиваем счетчик кадров
            frame_count += 1

            # Выводим заголовок с количеством обнаруженных объектов
            print(MSG_DETECTION_RESULT.format(
                timestamp=timestamp,
                count=len(detections)
            ))

            # Выводим детальную информацию о каждом обнаруженном объекте
            if len(detections) > 0:
                for det in detections:
                    print(MSG_OBJECT_DETECTED.format(
                        class_name=det['class_name'],
                        confidence=det['confidence']
                    ))
            else:
                # Если ничего не обнаружено
                print("  - (объекты не обнаружены)")

            # Выводим текущий эликсир
            print(f"  - Эликсир противника: {elixir_balance:.1f} / {ELIXIR_MAX}")

            # --- КОНТРОЛЬ ЧАСТОТЫ КАДРОВ ---
            # Вычисляем время, затраченное на обработку
            total_time = time.time() - start_time

            # Вычисляем время каждого этапа
            frame_time = time_after_capture - start_time
            detection_time = time_after_detection - time_after_capture

            print(f"Время захвата:               {frame_time:.2f} сек")
            print(f"Время детекции:              {detection_time:.2f} сек")
            if DETECTION_TEST:
                save_time = time_after_save - time_after_detection
                print(f"Время сохранения:            {save_time:.2f} сек")
            print(f"Время всей обработки:        {total_time:.2f} сек")

            print()  # Пустая строка для разделения

            # --- ОБНОВЛЕНИЕ OVERLAY ОКОН ---
            # Обновляем GUI overlay окон чтобы они оставались отзывчивыми (живыми)
            if overlay_static:
                overlay_static.update()
            if overlay_dynamic:
                overlay_dynamic.update()

            # Вычисляем время ожидания до следующего кадра
            sleep_time = frame_interval - total_time

            # Если обработка заняла меньше времени чем интервал, ждем
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        # Обработка прерывания программы (Ctrl+C)
        print()
        print("Программа прервана пользователем (Ctrl+C)")

    except Exception as e:
        # Обработка непредвиденных ошибок
        print()
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")

    finally:
        # ===== ШАГ 5: ОЧИСТКА РЕСУРСОВ =====
        # Блок finally выполнится в любом случае (нормальное завершение или ошибка)
        print()
        print("Очистка ресурсов.")

        # Закрываем overlay окна (в обратном порядке создания)
        if overlay_dynamic:
            overlay_dynamic.close()
        if overlay_static:
            overlay_static.close()

        # Закрываем объект захвата экрана
        screen_capture.cleanup()

        # Выводим статистику
        print(f"Обработано кадров: {frame_count}")
        print("Программа завершена.")
        print("=" * 60)


# ===== ТОЧКА ВХОДА В ПРОГРАММУ =====
if __name__ == "__main__":
    main()
