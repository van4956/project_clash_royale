# -*- coding: utf-8 -*-
"""
Главный файл приложения Clash Royale Bot
Точка входа в программу.
"""
import logging

# Настраиваем конфигурацию логирования
# WARNING - самое важное, для прода
# INFO - подробный, для отладки
logging.basicConfig(level=logging.WARNING, format='  -  [%(asctime)s] #%(levelname)-5s -  %(name)s:%(lineno)d  -  %(message)s')
logger = logging.getLogger(__name__)

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
    MSG_DETECTION_RESULT,       # Шаблон сообщения о результатах детекции
    MSG_OBJECT_DETECTED,        # Шаблон сообщения об обнаруженном объекте
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
    1. Инициализация модулей (ScreenCapture, CardDetector)
    2. Выбор области экрана (ROI)
    3. Создание overlay элементов (статичные и динамические)
    4. Загрузка модели YOLO
    5. Инициализация Game State
    6. Основной цикл:
        - Захват кадра
        - Детекция YOLO
        - Проверка технических классов (_ start, _ timer total, _ finish)
        - Обработка детекций через detection_handler
        - Обновление overlay и вывод в терминал
    7. Очистка ресурсов при завершении
    """

    print("=" * 80)
    print("Clash Royale Bot")
    print("=" * 80)


    # ===== ШАГ 1: ИНИЦИАЛИЗАЦИЯ МОДУЛЕЙ =====
    logger.info("Инициализация модулей...")

    # Создаем объект для захвата экрана
    screen_capture = ScreenCapture()

    # Создаем объект детектора карт
    detector = CardDetector()

    logger.info("Модули инициализированы ✓ ")



    # ===== ШАГ 2: ВЫБОР ОБЛАСТИ ЭКРАНА =====
    logger.info("Настройка области экрана...")

    # Пытаемся загрузить сохраненные координаты из файла
    if not screen_capture.load_roi():
        # Если файл не найден, запускаем интерактивный выбор области
        logger.info("Сохраненные координаты не найдены!")
        logger.info("Запуск режима выбора области экрана...")

        roi = screen_capture.select_roi()

        # Если пользователь отменил выбор (нажал ESC), завершаем программу
        if roi is None:
            logger.warning("Программа завершена пользователем!")
            return

    logger.info("Область экрана настроена ✓ ")



    # ===== ШАГ 3: СОЗДАНИЕ OVERLAY ЭЛЕМЕНТОВ =====
    # Создание статичного overlay
    logger.info("Создание статичного overlay...")

    # Проверяем что ROI установлен
    if screen_capture.roi is None:
        logger.error("ОШИБКА: ROI не установлен. Завершение программы!")
        return

    # Вычисляем параметры относительно размера ROI
    roi_width = screen_capture.roi['width']
    roi_height = screen_capture.roi['height']

    # --- ПАРАМЕТРЫ ДЛЯ ДОСКИ ---
    board_width = int(roi_width * BOARD_WIDTH_PERCENT)
    board_height = int(roi_height * BOARD_HEIGHT_PERCENT)
    board_x = screen_capture.roi['left']
    board_y = screen_capture.roi['top']

    # --- ПАРАМЕТРЫ ДЛЯ КАПЕЛЬКИ ---
    drop_indent_percent = int(roi_width * ELIXIR_DROP_INDENT_PERCENT)
    drop_x = screen_capture.roi['left'] + drop_indent_percent
    drop_y = screen_capture.roi['top'] + drop_indent_percent
    drop_width = int(roi_width * ELIXIR_DROP_SIZE_PERCENT)

    # --- СОЗДАЕМ СТАТИЧНЫЙ OVERLAY (доска + капелька) ---
    drop_image_path = os.path.join("data", "drop_elixir.png")
    overlay_static = StaticOverlay(
        drop_image_path, drop_x, drop_y, drop_width,
        board_x, board_y, board_width, board_height, BOARD_ALPHA, BOARD_COLOR
    )

    if not overlay_static.create_windows():
        logger.warning("Не удалось создать статичный overlay (продолжаем без него)!")
        overlay_static = None

    # Небольшая задержка для правильного отображения
    time.sleep(0.05)
    # Создание динамического overlay
    logger.info("Создание динамического overlay...")
    # Получаем реальные размеры капельки после масштабирования
    drop_height = overlay_static.height

    # --- ПАРАМЕТРЫ ДЛЯ ШКАЛЫ ---
    # Высота, ширина
    bar_width = int(roi_width * ELIXIR_BAR_WIDTH_PERCENT)
    bar_height = int(drop_height * ELIXIR_BAR_HEIGHT_RATIO)

    # Позиция шкалы (справа от капельки, центрирована вертикально)
    bar_x = drop_x + drop_width + int(drop_height * ELIXIR_BAR_OFFSET_RATIO)
    bar_y = drop_y

    # --- СОЗДАЕМ ДИНАМИЧНЫЙ OVERLAY (шкала, цифра, карты) ---
    overlay_dynamic = DynamicOverlay(
        bar_x, bar_y, bar_width, bar_height,
        drop_x, drop_y, drop_width, drop_height,
        board_y, board_height
    )

    if not overlay_dynamic.create_window():
        logger.warning("Не удалось создать динамический overlay!")
        overlay_dynamic = None



    # ===== ШАГ 4: ЗАГРУЗКА МОДЕЛИ YOLO =====
    logger.info("Загрузка модели YOLO...")

    # Загружаем обученную модель
    if not detector.load_model():
        # Если загрузка не удалась, завершаем программу
        logger.error("Не удалось загрузить модель. Завершение программы.")
        screen_capture.cleanup()
        return

    logger.info("Модель загружена ✓ ")

    # --- ПОДГОТОВКА ПАПКИ detection/ (если включен режим отладки) ---
    if DETECTION_TEST:
        logger.info("Подготовка папки для сохранения кадров...")
        # Создаем папку для сохранения кадров если её нет
        if not os.path.exists(DETECTION_OUTPUT_DIR):
            os.makedirs(DETECTION_OUTPUT_DIR)
            logger.info("Создана папка для сохранения кадров: %s ✓ ",DETECTION_OUTPUT_DIR)
        else:
            logger.info("Режим отладки активен. Кадры будут сохраняться в папку %s", DETECTION_OUTPUT_DIR)



    # ===== ШАГ 5: ИНИЦИАЛИЗАЦИЯ GAME STATE =====
    logger.info("Инициализация Game State...")
    game_state = GameState()
    logger.info("Game State инициализирован ✓ ")



    # ===== ШАГ 6: ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ =====
    print("=" * 80)
    print("Запуск захвата экрана...")
    print(f"Частота обработки: {FPS} кадров/сек")
    print("Нажмите 'Ctrl+C' в терминале для остановки программы")
    print("=" * 80)

    # Вычисляем интервал между кадрами в секундах
    frame_interval = 1.0 / FPS

    # Счетчик обработанных кадров
    frame_count = 0

    # Флаги инициализации игры
    game_pre_start = True  # Флаг предстартового ожидания (ожидаем _ start)
    game_start_timer = True      # Флаг начала игры (ожидаем _ timer total)
    game_finished = False      # Флаг конца игры (ожидаем _ finish)
    game_reset = False      # Флаг сброса игры

    try:
        while True:
            # Засекаем время начала обработки кадра
            start_time = time.time()

            # --- 6.1: ЗАХВАТ КАДРА ---

            # Захватываем текущий кадр из выбранной области экрана
            frame = screen_capture.capture_frame()
            time_after_capture = time.time()

            # Если кадр не получен, пропускаем итерацию
            if frame is None:
                logger.warning("Кадр не получен! Пропускаем итерацию...")
                time.sleep(frame_interval)
                continue

            # --- 6.2: ДЕТЕКЦИЯ КАРТ ---

            # Отправляем кадр в YOLO модель для детекции карт
            detections = detector.detect(frame)
            time_after_detection = time.time()

            # Текущая временная метка (timestamp в секундах с начала эпохи)
            current_time = time.time()

            # --- 6.3: ОБРАБОТКА ТЕХНИЧЕСКИХ КЛАССОВ ---

            game_start_timer = True # TODO: удалить после тестирования
            game_pre_start = True # TODO: удалить после тестирования
            # game_state.card_manager.reset() # TODO: удалить после тестирования
            game_state.game_start_time = current_time # TODO: удалить после тестирования


            # YOLO модель пока еще не научена детектить '_ start'
            # Проверка на начало боя (_ start) - подготовка колоды
            # if not game_start_timer:
            #     for det in detections:
            #         if det['class_name'] == '_ start':
            #             print("\nОбнаружен _ start - подготовка колоды противника")
            #             game_state.card_manager.reset()
            #             game_start_timer = True
            #             break

            # Проверка на первый таймер (_ timer total) - старт игрового режима
            # if game_start_timer and not game_pre_start:
            #     for det in detections:
            #         if det['class_name'] == '_timer_red':
            #             print("Обнаружен первый _ timer total - старт игрового режима\n")
            #             game_state.card_manager.reset() # TODO: удалить после тестирования
            #             game_state.game_start_time = current_time
            #             game_state.time_screen = current_time
            #             game_pre_start = True
            #             break

            # Проверка на конец боя (_ finish)
            game_finished = False
            for det in detections:
                if det['class_name'] == '_ finish':
                    game_finished = True
                    break


            # --- 6.4: ОБРАБОТКА ДЕТЕКЦИЙ (если игра началась) ---
            if game_pre_start and not game_finished:

                # --- 6.4.1: КООРДИНАТОР ОБРАБОТКИ ДЕТЕКЦИЙ ---
                results = process_detections(
                    all_detections=detections,
                    current_time=current_time,
                    game_state=game_state,
                    all_cards=all_card
                )
                time_after_processing = time.time()

                # --- 6.3.2: ОБНОВЛЕНИЕ ДИНАМИЧЕСКОГО OVERLAY (шкала + цифра + карты) ---
                if overlay_dynamic:
                    # Обновляем эликсир
                    overlay_dynamic.update_display(game_state.elixir_balance)

                    # Обновляем карты (await и hand)
                    await_cards = game_state.card_manager.get_await_cards()
                    hand_cards = game_state.card_manager.get_hand_cards()
                    overlay_dynamic.set_await_cards(await_cards)
                    overlay_dynamic.set_hand_cards(hand_cards)

                time_after_overlay_update = time.time()
            else:
                # Если игра не началась, устанавливаем метки времени равными предыдущей
                time_after_processing = time_after_detection
                time_after_overlay_update = time_after_detection

            # --- 6.4: ОБРАБОТКА КОНЦА ИГРЫ ---
            if game_finished and game_pre_start:
                logger.info("КОНЕЦ БОЯ")
                logger.info("Эликсир ушедший в минус: %s", game_state.elixir_negative)
                logger.info("Простаиваемый эликсир:   %s", game_state.elixir_stagnation)

                # Сброс состояния игры
                game_state.reset()
                game_start_timer = False
                game_pre_start = False



            # --- 6.5: СОХРАНЕНИЕ КАДРА С ДЕТЕКЦИЯМИ (если включен режим отладки) ---
            if DETECTION_TEST:
                # Рисуем детекции на кадре (боксы, названия, confidence)
                frame_with_detections = detector.draw_detections(frame, detections)

                # Генерируем имя файла по текущему времени (HH-MM-SS-ms.png)
                save_timestamp = datetime.now()
                filename = save_timestamp.strftime("%H-%M-%S-") + f"{save_timestamp.microsecond // 1000:03d}.png"
                filepath = os.path.join(DETECTION_OUTPUT_DIR, filename)

                # Сохраняем изображение
                cv2.imwrite(filepath, frame_with_detections)
                time_after_save = time.time()
            else:
                time_after_save = time_after_overlay_update



            # --- 6.6: ВЫВОД РЕЗУЛЬТАТОВ В ТЕРМИНАЛ ---
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


            # --- ИНФОРМАЦИЯ О СОСТОЯНИИ ИГРЫ ---
            if game_pre_start and not game_finished:
                # Выводим информацию о балансе элексира
                balance = game_state.get_elixir_metrics()['balance']
                negative = game_state.get_elixir_metrics()['negative']
                stagnation = game_state.get_elixir_metrics()['stagnation']
                print(f"Elix:  {balance:.1f}  -{negative:.1f}  +{stagnation:.1f}")
                # Выводим информацию о цикле карт
                hand_cards = game_state.card_manager.get_hand_cards()
                await_cards = game_state.card_manager.get_await_cards()

                hand_names = [card.card_name if card.card_name else "???" for card in hand_cards]
                await_names = [card.card_name if card.card_name else "???" for card in await_cards]

                print(f"Away:  {', '.join(await_names)}")
                print(f"Hand:  {', '.join(hand_names)}")

            elif not game_start_timer:
                logger.info("Ожидание начала боя (_start)...")
            elif not game_pre_start:
                logger.info("Ожидание старта игры (_timer_total)...")

            # --- 6.7: ОБНОВЛЕНИЕ OVERLAY ОКОН ---
            # Обновляем GUI overlay окон чтобы они оставались отзывчивыми (живыми)
            if overlay_static:
                overlay_static.update()
            if overlay_dynamic:
                overlay_dynamic.update()

            # --- 6.8: КОНТРОЛЬ ЧАСТОТЫ КАДРОВ ---
            # Вычисляем время, затраченное на обработку
            total_time = time.time() - start_time

            # Вычисляем время каждого этапа
            frame_time = time_after_capture - start_time
            detection_time = time_after_detection - time_after_capture
            processing_time = time_after_processing - time_after_detection
            overlay_update_time = time_after_overlay_update - time_after_processing
            if DETECTION_TEST:
                save_time = time_after_save - time_after_overlay_update
            else:
                save_time = 0

            print("Time:  общее = захват   детекция  обработка  overlay  сохранение")
            print(f"Time:  {total_time:.3f} = {frame_time:.3f}  +  {detection_time:.3f}  +  {processing_time:.3f}  +  {overlay_update_time:.3f}  +  {save_time:.3f}")
            print()


            # Вычисляем время ожидания до следующего кадра
            sleep_time = frame_interval - total_time

            # Если обработка заняла меньше времени чем интервал, ждем
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:

        logger.info("Программа прервана пользователем (Ctrl+C)")

    except Exception as e:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: %s", e)

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
        print("=" * 80)


# ===== ТОЧКА ВХОДА В ПРОГРАММУ =====
if __name__ == "__main__":
    main()
