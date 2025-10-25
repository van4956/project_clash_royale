"""
Модуль для обработки абилок чемпионов (Champion Abilities).
Абилки НЕ влияют на цикл карт, только на баланс эликсира.
Определение владельца абилки по наличию красного уровня чемпиона в зоне над абилкой.
"""

import logging

# Настраиваем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)

from typing import Dict, List, Any, Optional, Tuple
from modules.classes import Card


def check_ability_dict_timeout(
    ability_dict_enemy: Dict[str, float],
    current_time: float
) -> None:
    """
    Проверяет таймауты ВРАЖЕСКИХ абилок и удаляет истекшие записи.

    Args:
        ability_dict_enemy: словарь таймаутов ВРАЖЕСКИХ абилок {"AC_xxx": timeout_end, ...}
        current_time: текущая временная метка

    Логика:
        - Проходим по всем записям в ability_dict_enemy
        - Если current_time >= timeout_end → таймаут истек → удаляем запись
        - Это означает что абилка уже отыгралась
    """
    # Создаем список для удаления (нельзя изменять словарь во время итерации)
    to_remove = []

    for class_name, timeout_end in ability_dict_enemy.items():
        if current_time >= timeout_end:
            # Таймаут истек → помечаем для удаления
            to_remove.append(class_name)

    # Удаляем истекшие записи
    for class_name in to_remove:
        del ability_dict_enemy[class_name]


def _is_box_in_zone(box: Tuple[float, float, float, float], zone: Tuple[float, float, float, float]) -> bool:
    """
    Проверяет находится ли центр бокса внутри зоны.

    Args:
        box: бокс для проверки (x1, y1, x2, y2)
        zone: зона (x1, y1, x2, y2)

    Returns:
        True если центр бокса в зоне

    Логика:
        - Вычисляем центр бокса
        - Проверяем вхождение центра в зону
    """
    # Центр бокса
    box_center_x = (box[0] + box[2]) / 2
    box_center_y = (box[1] + box[3]) / 2

    # Проверка вхождения в зону
    return (zone[0] <= box_center_x <= zone[2] and
            zone[1] <= box_center_y <= zone[3])


def _find_red_level_in_zone(
    box_ability: Tuple[float, float, float, float],
    all_detections: List[Dict[str, Any]]
) -> bool:
    """
    Ищет красный уровень чемпиона (_lvl_red_cham) в зоне над абилкой.

    Args:
        box_ability: бокс абилки (x1, y1, x2, y2)
        all_detections: все детекции текущего кадра

    Returns:
        True если найден красный уровень в зоне, False иначе

    Логика:
        1. Расширяем box_ability ВВЕРХ на полкорпуса (0.5 высоты)
        2. Ищем детекции "_lvl_red_cham" в all_detections
        3. Проверяем пересечение через _is_box_in_zone()
        4. Если нашли хотя бы один → возвращаем True

    Обоснование:
        Абилки визуализируются на месте чемпиона или рядом с ним.
        У вражеского чемпиона виден красный уровень.
        Если находим красный уровень над/рядом с абилкой → это ВРАЖЕСКАЯ абилка.
    """
    x1, y1, x2, y2 = box_ability
    h = y2 - y1  # высота абилки

    # Зона поиска: расширяем вверх на полкорпуса (0.5 высоты)
    search_zone = (x1, y1 - h * 0.5, x2, y2)

    # Ищем красный уровень в детекциях
    for detection in all_detections:
        class_name = detection.get('class_name', '')
        if class_name == '_lvl_red_cham':
            # Получаем бокс красного уровня
            box_lvl = detection.get('box')  # (x1, y1, x2, y2)
            if box_lvl and _is_box_in_zone(box_lvl, search_zone):
                # Красный уровень найден в зоне!
                return True

    # Красный уровень не найден
    return False


def _find_card_by_ability_class_name(
    class_name: str,
    all_cards: List[Card]
) -> Optional[Card]:
    """
    Вспомогательная функция для поиска карты чемпиона по ability_class_name.

    Args:
        class_name: ability_class_name для поиска
        all_cards: список всех карт

    Returns:
        Card если найдена, None иначе
    """
    for card in all_cards:
        if card.ability_class_name == class_name:
            return card
    return None


def process_ability_detections(
    all_detections: List[Dict[str, Any]],
    ability_dict_enemy: Dict[str, float],
    current_time: float,
    all_cards: List[Card]
) -> float:
    """
    Главная функция обработки абилок чемпионов.

    Args:
        all_detections: все детекции текущего кадра
        ability_dict_enemy: словарь таймаутов ВРАЖЕСКИХ активных абилок
        current_time: текущая временная метка
        all_cards: список всех карт

    Returns:
        float: суммарный потраченный эликсир в текущей итерации

    Логика (последовательность):
        1. Очистка истекших таймаутов ability_dict_enemy
        2. Обработка детекций абилок:
           - Ищем абилки в all_detections (class_name начинается с "A": AC, AR, AE, AL)
           - Для каждой абилки:
             a) Проверяем ability_dict_enemy → если ЕСТЬ → уже обработана → игнорируем
             b) Ищем красный уровень (_lvl_red_cham) в зоне над абилкой
             c) Если НАШЛИ красный уровень:
                - Это ВРАЖЕСКАЯ абилка
                - Списываем эликсир (абилки НЕ влияют на цикл карт!)
                - Блокируем повторную обработку через ability_dict_enemy
             d) Если НЕ нашли красный уровень:
                - Это НАША абилка → просто игнорируем
        3. Возврат суммарного elixir_spent

    Особенности:
        - Абилки НЕ влияют на цикл карт противника (не запускаем play_known_card/play_new_card)
        - Максимум 1 чемпион в колоде (8 карт) → максимум 1 абилка одновременно
        - Стоимость абилок низкая (1-2 элека) → некритично если пропустим детекцию
        - Определение владельца по красному уровню чемпиона (надежная проверка)
        - НЕТ Zone icons для абилок (в отличие от заклинаний)
    """
    # 1. Очистка истекших таймаутов ВРАЖЕСКИХ абилок
    check_ability_dict_timeout(ability_dict_enemy, current_time)

    # 2. Обработка детекций абилок
    elixir_spent_total = 0.0

    for detection in all_detections:
        class_name = detection.get('class_name', '')

        # Фильтруем абилки чемпионов (начинаются с "A": AC, AR, AE, AL)
        if not (class_name and class_name.startswith('A') and len(class_name) > 1):
            continue

        # Проверяем что это действительно абилка чемпиона
        card = _find_card_by_ability_class_name(class_name, all_cards)
        if not card or not card.champion:
            continue

        # a) Проверяем ability_dict_enemy
        if class_name in ability_dict_enemy:
            # Абилка уже обработана → игнорируем
            continue

        # b) Ищем красный уровень в зоне над абилкой
        box_ability = detection.get('box')  # (x1, y1, x2, y2)
        if not box_ability:
            continue

        has_red_level = _find_red_level_in_zone(box_ability, all_detections)

        # c) ВРАЖЕСКАЯ абилка (красный уровень найден)
        if has_red_level:
            # Списываем эликсир (абилки НЕ влияют на цикл карт!)
            elixir_spent_total += card.ability_elixir

            # Блокируем повторную обработку
            if card.ability_life_time:
                timeout_end = current_time + card.ability_life_time
                ability_dict_enemy[class_name] = timeout_end

        # d) НАША абилка (красный уровень НЕ найден)
        # Просто игнорируем, ничего не делаем

    # 3. Возврат суммарного elixir_spent
    return elixir_spent_total
