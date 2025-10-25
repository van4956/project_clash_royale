"""
Модуль для обработки маркеров эволюций (Evolution Markers).
Маркеры сигнализируют что была сыграна карта с эволюцией.
Подсвечивают ТОЛЬКО вражеские эволюции (наши не подсвечиваются).
"""

import os
import logging

# Настраиваем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)

from typing import Dict, List, Any

# Константа: время отображения маркера эволюции на поле (в секундах)
EVO_MARKER_DISPLAY_TIME = 3.0


def check_evolution_dict_timeout(
    evolution_dict_timer: Dict[float, str],
    current_time: float
) -> None:
    """
    Проверяет таймауты маркеров эволюции и удаляет истекшие записи.

    Args:
        evolution_dict_timer: словарь таймеров маркеров {timestamp: status, ...}
                             status: "detect" (обнаружен) или "record" (учтен)
        current_time: текущая временная метка

    Логика:
        - Проходим по всем ключам (timestamp) в evolution_dict_timer
        - Если current_time >= timestamp → таймаут истек → удаляем запись
        - Маркер уже исчез с поля
    """
    # Создаем список для удаления (нельзя изменять словарь во время итерации)
    to_remove = []

    for timestamp in evolution_dict_timer.keys():
        if current_time >= timestamp:
            # Таймаут истек → помечаем для удаления
            to_remove.append(timestamp)

    # Удаляем истекшие записи
    for timestamp in to_remove:
        del evolution_dict_timer[timestamp]


def process_evolution_detections(
    all_detections: List[Dict[str, Any]],
    evolution_dict_timer: Dict[float, str],
    current_time: float
) -> None:
    """
    Главная функция обработки маркеров эволюций.

    Args:
        all_detections: все детекции текущего кадра
        evolution_dict_timer: словарь таймеров маркеров {timestamp: status, ...}
        current_time: текущая временная метка

    Логика (последовательность):
        1. Очистка истекших таймеров в evolution_dict_timer
        2. Подсчет детектированных маркеров эволюции (_evolution_mark)
        3. Сравнение с количеством известных маркеров (ключей в словаре)
        4. Если detected > known → новые маркеры:
           - Добавляем новые записи в evolution_dict_timer
           - Ключ = timestamp (current_time + EVO_MARKER_DISPLAY_TIME)
           - Значение = "detect" (обнаружен, но еще не учтен в cnt_evo)

    Примечание:
        Обновление cnt_evo карты происходит в card_manager.py (при отыгрывании карты).
        Здесь мы только фиксируем появление новых маркеров со статусом "detect".

    Статусы маркеров:
        "detect" - маркер обнаружен, но еще не учтен в cnt_evo карты
        "record" - маркер учтен (cnt_evo += 1), статус меняется в card_manager.py
    """
    # 1. Очистка истекших таймеров
    check_evolution_dict_timeout(evolution_dict_timer, current_time)

    # 2. Подсчет детектированных маркеров эволюции
    detected_markers = 0

    for detection in all_detections:
        class_name = detection.get('class_name', '')
        # Маркер эволюции: _ evolution mark
        if class_name == '_ evolution mark':
            detected_markers += 1

    # 3. Сравнение с известными маркерами
    known_markers = len(evolution_dict_timer)

    # 4. Обработка новых маркеров
    if detected_markers > known_markers:
        # Появились новые маркеры!
        new_markers_count = detected_markers - known_markers

        # Добавляем новые записи в evolution_dict_timer
        for _ in range(new_markers_count):
            # Timestamp = текущее время + время отображения маркера
            timestamp = current_time + EVO_MARKER_DISPLAY_TIME

            # Статус = "detect" (обнаружен, но еще не учтен)
            # Статус будет изменен на "record" в card_manager.py при обновлении cnt_evo
            evolution_dict_timer[timestamp] = "detect"


def find_oldest_detect_marker(evolution_dict_timer: Dict[float, str]) -> float | None:
    """
    Находит самый СТАРШИЙ (earliest) маркер со статусом "detect".

    Args:
        evolution_dict_timer: словарь таймеров маркеров {timestamp: status, ...}

    Returns:
        timestamp самого старшего маркера со статусом "detect", или None если таких нет

    Логика:
        - Фильтруем ключи по статусу "detect"
        - Находим минимальный timestamp (самый старый по времени создания)
        - Возвращаем этот timestamp

    Примечание:
        Эта функция используется в card_manager.py для определения какой маркер учесть.
        Самый старший маркер = первый необработанный маркер.
    """
    # Фильтруем ключи со статусом "detect"
    detect_markers = [
        timestamp for timestamp, status in evolution_dict_timer.items()
        if status == "detect"
    ]

    # Если есть маркеры со статусом "detect" → возвращаем самый старый (минимальный timestamp)
    if detect_markers:
        return min(detect_markers)

    # Нет маркеров со статусом "detect"
    return None


def mark_evolution_as_recorded(
    evolution_dict_timer: Dict[float, str],
    timestamp: float
) -> None:
    """
    Меняет статус маркера с "detect" на "record".

    Args:
        evolution_dict_timer: словарь таймеров маркеров {timestamp: status, ...}
        timestamp: ключ маркера для изменения статуса

    Логика:
        - Меняем статус указанного маркера на "record"
        - Означает что маркер учтен в cnt_evo карты

    Примечание:
        Эта функция вызывается из card_manager.py после обновления cnt_evo.
    """
    if timestamp in evolution_dict_timer:
        evolution_dict_timer[timestamp] = "record"
