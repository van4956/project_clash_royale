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
from modules.game_state import GameState  # Глобальное состояние игры
from modules.detection_handler import process_detections  # Координатор обработки детекций
from modules.all_card import all_card  # Список всех карт для поиска атрибутов

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
    ELIXIR_BAR_OFFSET_RATIO     # Отступ шкалы от капельки
)


def main():
    """
    Главная функция приложения

    Последовательность работы:
    1. Инициализация модулей (захват экрана, детектор)
    2. Выбор области экрана (ROI)
    3. Создание статичного overlay (доска, капелька)
    4. Загрузка модели YOLO
    5. Инициализация Game State
    6. Основной цикл:
        - Захват кадра
        - Детекция YOLO
        - Проверка технических классов (_ vs, _ timer total, _ finish)
        - Обработка детекций через detection_handler
        - Обновление overlay и вывод в терминал
    7. Очистка ресурсов при завершении
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

        # === СОЗДАЕМ ДИНАМИЧНЫЙ OVERLAY (шкала, цифра, карты) ===
        overlay_dynamic = DynamicOverlay(
            bar_x, bar_y, bar_width, bar_height,
            drop_x, drop_y, drop_width, drop_height,
            board_y, board_height
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


    # ===== ШАГ 5: ИНИЦИАЛИЗАЦИЯ GAME STATE =====
    print("-> Инициализация Game State...")
    game_state = GameState()
    print("✓ Game State инициализирован")
    print()


    # ===== ПОДГОТОВКА ПАПКИ detection/ ДЛЯ СОХРАНЕНИЯ КАДРОВ =====
    if DETECTION_TEST:
        # Создаем папку для сохранения кадров если её нет
        if not os.path.exists(DETECTION_OUTPUT_DIR):
            os.makedirs(DETECTION_OUTPUT_DIR)
            print(f"✓ Создана папка для сохранения кадров: {DETECTION_OUTPUT_DIR}")
        else:
            print(f"Режим отладки активен.\nКадры будут сохраняться в папку {DETECTION_OUTPUT_DIR}")
        print()


    # ===== ШАГ 6: ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ =====
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

    # Флаги инициализации игры
    game_initialized = False  # Флаг инициализации колоды после _ vs
    game_started = False      # Флаг начала игры после первого _ timer total

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

            # Текущая временная метка (timestamp в секундах с начала эпохи)
            current_time = time.time()

            # --- ОБРАБОТКА ТЕХНИЧЕСКИХ КЛАССОВ ---

            game_initialized = True # TODO: удалить после тестирования
            game_started = True # TODO: удалить после тестирования
            game_state.card_manager.reset() # TODO: удалить после тестирования
            game_state.game_start_time = current_time # TODO: удалить после тестирования
            game_state.time_screen = current_time # TODO: удалить после тестирования

            # YOLO модель пока еще не научена детектить '_ vs'
            # Проверка на начало боя (_ vs) - подготовка колоды
            # if not game_initialized:
            #     for det in detections:
            #         if det['class_name'] == '_ vs':
            #             print("\nОбнаружен _ vs - подготовка колоды противника")
            #             game_state.card_manager.reset()
            #             game_initialized = True
            #             break

            # Проверка на первый таймер (_ timer total) - старт игрового режима
            # if game_initialized and not game_started:
            #     for det in detections:
            #         if det['class_name'] == '_timer_red':
            #             print("Обнаружен первый _ timer total - старт игрового режима\n")
            #             game_state.card_manager.reset() # TODO: удалить после тестирования
            #             game_state.game_start_time = current_time
            #             game_state.time_screen = current_time
            #             game_started = True
            #             break

            # Проверка на конец боя (_ finish)
            game_finished = False
            for det in detections:
                if det['class_name'] == '_ finish':
                    game_finished = True
                    break

            # --- ОБРАБОТКА ДЕТЕКЦИЙ (если игра началась) ---
            if game_started and not game_finished:
                # Вызываем координатор обработки детекций
                results = process_detections(
                    all_detections=detections,
                    current_time=current_time,
                    game_state=game_state,
                    all_cards=all_card
                )

                # Обновляем динамический overlay (шкала + цифра + карты)
                if overlay_dynamic:
                    # Обновляем эликсир
                    overlay_dynamic.update_display(game_state.elixir_balance)

                    # Обновляем карты (await и hand)
                    await_cards = game_state.card_manager.get_await_cards()
                    hand_cards = game_state.card_manager.get_hand_cards()
                    overlay_dynamic.set_await_cards(await_cards)
                    overlay_dynamic.set_hand_cards(hand_cards)

            # --- ОБРАБОТКА КОНЦА ИГРЫ ---
            if game_finished and game_started:
                print("\n" + "=" * 60)
                print("КОНЕЦ БОЯ - Обнаружен _ finish")
                print("=" * 60)
                print(f"Эликсир ушедший в минус: {game_state.elixir_negative:.2f}")
                print(f"Простаиваемый эликсир:   {game_state.elixir_stagnation:.2f}")
                print("=" * 60)
                print()

                # Сброс состояния игры
                game_state.reset()
                game_initialized = False
                game_started = False

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
            # else:
            #     # Если ничего не обнаружено
            #     print("  - (объекты не обнаружены)")

            # --- ИНФОРМАЦИЯ О СОСТОЯНИИ ИГРЫ ---
            if game_started and not game_finished:
                # # Выводим текущий эликсир противника
                # print(f"  💧 Эликсир противника: {game_state.elixir_balance:.1f} / 10.0")

                # # Выводим информацию о потраченном эликсире (если было)
                # if 'results' in locals() and results['total_elixir_spent'] > 0:
                #     print(f"  💰 Потрачено в этом кадре: {results['total_elixir_spent']:.1f}")
                #     if results['elixir_spent_timer'] > 0:
                #         print(f"     └─ Таймеры: {results['elixir_spent_timer']:.1f}")
                #     if results['elixir_spent_spell'] > 0:
                #         print(f"     └─ Заклинания: {results['elixir_spent_spell']:.1f}")
                #     if results['elixir_spent_ability'] > 0:
                #         print(f"     └─ Абилки: {results['elixir_spent_ability']:.1f}")

                # Выводим информацию о цикле карт
                hand_cards = game_state.card_manager.get_hand_cards()
                await_cards = game_state.card_manager.get_await_cards()

                hand_names = [card.card_name if card.card_name else "???" for card in hand_cards]
                await_names = [card.card_name if card.card_name else "???" for card in await_cards]

                print(f"  ⏳ Ожидание: {', '.join(await_names)}")
                print(f"  🃏 Рука:     {', '.join(hand_names)}")

            elif not game_initialized:
                print("  ->  Ожидание начала боя (_ vs)...")
            elif not game_started:
                print("  ->  Ожидание старта игры (_ timer total)...")

            # --- ОБНОВЛЕНИЕ OVERLAY ОКОН ---
            # Обновляем GUI overlay окон чтобы они оставались отзывчивыми (живыми)
            if overlay_static:
                overlay_static.update()
            if overlay_dynamic:
                overlay_dynamic.update()

            # --- КОНТРОЛЬ ЧАСТОТЫ КАДРОВ ---
            # Вычисляем время, затраченное на обработку
            total_time = time.time() - start_time

            # Вычисляем время каждого этапа
            frame_time = time_after_capture - start_time
            detection_time = time_after_detection - time_after_capture

            print(f"Время захвата кадра:         {frame_time:.2f} сек")
            print(f"Время детекции YOLO:         {detection_time:.2f} сек")
            print("Время обработки детекций:     сек")
            print("Время обновления overlay:     сек")
            if DETECTION_TEST:
                save_time = time_after_save - time_after_detection
                print(f"Время сохранения скринов:     {save_time:.2f} сек")
            print(f"Общее время обработки:       {total_time:.2f} сек")

            print()  # Пустая строка для разделения

            # Вычисляем время ожидания до следующего кадра
            sleep_time = frame_interval - total_time

            # Если обработка заняла меньше времени чем интервал, ждем
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print()
        print("Программа прервана пользователем (Ctrl+C)")

    except Exception as e:
        print()
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")

    finally:

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
