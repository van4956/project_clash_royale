"""
Модуль для обработки заклинаний (Spells).
Отыгрыш заклинаний НЕ маркируется таймерами.
Определение происходит по детекции эффекта заклинания на поле и сопоставлению с нашими заклинаниями.
"""

import logging

# Настраиваем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)

from typing import Dict, List, Any, Optional
from modules.classes import Card
from modules.card_manager import CardManager


def cleanup_spell_dict_hand(spell_dict_hand: Dict[str, List[int]]) -> None:
    """
    Очистка хвостов spell_dict_hand - сдвиг скользящего окна.
    Удаляет последний элемент (самый старый) из каждого списка.

    Args:
        spell_dict_hand: словарь наших заклинаний в руке
                        {"class_name": [1,0,0,0], "class_name": [1,1,1,1], ...}

    Логика:
        - Проходим по всем class_name в spell_dict_hand
        - У каждого списка удаляем последний элемент (pop)
        - Скользящее окно: [1,0,0,0] → [1,0,0] (после pop)
    """
    for class_name in spell_dict_hand:
        if spell_dict_hand[class_name]:  # если список не пуст
            spell_dict_hand[class_name].pop()  # удаляем последний элемент


def update_spell_dict_hand(
    all_detections: List[Dict[str, Any]],
    spell_dict_hand: Dict[str, List[int]],
    spell_dict_our: Dict[str, List[float]],
    current_time: float,
    all_cards: List[Card]
) -> None:
    """
    Обновляет список НАШИХ заклинаний в НАШЕЙ руке (spell_dict_hand).

    Args:
        all_detections: все детекции текущего кадра
        spell_dict_hand: словарь НАШИХ заклинаний в руке {"class_name": [1,0,0,0], ...}
        spell_dict_our: словарь списков таймаутов НАШИХ активных заклинаний {"class_name": [timeout_1, ...], ...}
        current_time: текущая временная метка
        all_cards: список всех карт для получения spell_life_time

    Логика:
        1. Ищем детекции заклинаний в НАШЕЙ руке (class_name начинается с "Z", особый нейминг для карт в НАШЕЙ руке)
        2. Для каждого найденного заклинания:
           - Если class_name есть в spell_dict_hand → добавляем 1 в начало списка
           - Если class_name НЕТ в spell_dict_hand → создаем новую запись [1,0,0,0]
        3. Для заклинаний которые НЕ детектированы:
           - Добавляем 0 в начало списка
        4. Проверяем на исчезновение (список стал [0,0,0,0]):
           - Переносим в spell_dict_our с таймаутом

    Примечание:
        CV модель возращает объекты с атрибутом class_name, в котором находится нейминг класса объекта (объекта модели).
        Любую карту можно задетектить в разных местах экрана.
        Поэтому все карты (объекты Card) имеют два атрибута, где прописаны разные class_name по которым CV модель их определяет.
        Атрибуты: class_name если это детекция на поле боя, и spell_my_hand_class_name если это детекция заклинания в НАШЕЙ руке.
        Если карта заклинания детектится в нижней части экрана, то есть в НАШЕЙ руке, то нейминг class_name CV модели начинается с "Z".
        Если карта заклинания детектится на поле боя, то class_name CV модели начинается с "S": SC, SE, SL.
    """
    # Находим все заклинания в текущих детекциях (НАША рука)
    # Обрабатываем все детекции с class_name начинающимся на "Z"
    detected_spells = set()
    for detection in all_detections:
        class_name = detection.get('class_name', '')
        # Фильтруем заклинания (начинаются с "Z")
        if class_name and class_name.startswith('Z') and len(class_name) > 1:
            detected_spells.add(class_name)

    # Обновляем spell_dict_hand
    # Для каждого известного заклинания добавляем 1 или 0 в начало списка
    for class_name in list(spell_dict_hand.keys()):
        if class_name in detected_spells:
            # Заклинание детектировано → добавляем 1 в начало
            spell_dict_hand[class_name].insert(0, 1)
        else:
            # Заклинание НЕ детектировано → добавляем 0 в начало
            spell_dict_hand[class_name].insert(0, 0)

        # Проверяем на исчезновение [0,0,0,0]
        if spell_dict_hand[class_name] == [0, 0, 0, 0]:
            # Заклинание исчезло из руки → переносим в spell_dict_our
            # Находим карту для получения spell_life_time
            card = _find_card_by_spell_my_hand_class_name(class_name, all_cards)
            # Если карта найдена и у нее есть время отыгрывания заклинания, то записываем в словарь spell_dict_our
            if card and card.spell_life_time:
                # Таймаут = текущее время + время отыгрывания заклинания
                timeout_end = current_time + card.spell_life_time
                # Записываем в словарь spell_dict_our по основному class_name (добавляем в список)
                if card.class_name:
                    card_class_name = card.class_name
                    # Создаем список если его нет, добавляем таймаут
                    if card_class_name not in spell_dict_our:
                        spell_dict_our[card_class_name] = []
                    spell_dict_our[card_class_name].append(timeout_end)

            # Удаляем из spell_dict_hand НАШЕ заклинание
            del spell_dict_hand[class_name]

    # Добавляем новые заклинания в spell_dict_hand
    for class_name in detected_spells:
        if class_name not in spell_dict_hand:
            # Новое заклинание в руке → создаем запись [1,0,0,0]
            spell_dict_hand[class_name] = [1, 0, 0, 0]


def check_spell_dict_timeout(
    spell_dict_timeout: Dict[str, List[float]],
    current_time: float
) -> None:
    """
    Проверяет таймауты в словаре заклинаний и удаляет истекшие записи.
    Универсальная функция для spell_dict_our и spell_dict_enemy.

    Args:
        spell_dict_timeout: словарь списков таймаутов {"class_name": [timeout_1, timeout_2], ...}
        current_time: текущая временная метка

    Логика:
        - Проходим по всем записям в spell_dict_timeout
        - Для каждого class_name фильтруем список таймаутов (удаляем истекшие)
        - Если список стал пустым → удаляем ключ целиком
        - Поддерживает до 2 одинаковых заклинаний одновременно (игровой лимит)
    """
    # Проходим по всем class_name
    for class_name in list(spell_dict_timeout.keys()):
        # Фильтруем список таймаутов - оставляем только активные (не истекшие)
        spell_dict_timeout[class_name] = [
            timeout for timeout in spell_dict_timeout[class_name]
            if current_time < timeout
        ]

        # Если список пуст (все таймауты истекли) → удаляем ключ
        if not spell_dict_timeout[class_name]:
            del spell_dict_timeout[class_name]


def _process_new_enemy_spell(
    class_name: str,
    card_manager: CardManager,
    all_cards: List[Card]
) -> Optional[Card]:
    """
    Обрабатывает ОДНО новое вражеское заклинание: запускает цикл карт и возвращает карту.

    Args:
        class_name: class_name детектированного заклинания на поле
        card_manager: менеджер карт противника
        all_cards: список всех карт для получения spell_life_time

    Returns:
        Card если заклинание обработано, None если карта не найдена

    Логика:
        1. Ищем карту в hand_cards → play_known_card()
        2. Если не нашли и есть card_random → ищем в deck_cards → play_new_card()
        3. Если не нашли → ищем в await_cards (сбой цикла)
        4. Если не нашли в card_manager → ищем в all_cards (для таймаута)
        5. Возвращаем найденную карту
    """
    found_card = None

    # Ищем карту в hand_cards
    if card_manager.is_card_in_hand(class_name):
        # Карта в руке → известная карта
        found_card = card_manager.find_card_in_deck(class_name)
        if found_card:
            card_manager.play_known_card(class_name)

    # Если не нашли в hand_cards и есть card_random → ищем в deck_cards
    elif card_manager.count_card_random_in_hand() > 0:
        found_card = card_manager.find_card_in_deck(class_name)
        if found_card:
            card_manager.play_new_card(class_name)

    # Если не нашли в deck_cards → ищем в await_cards (сбой цикла)
    elif card_manager.is_card_in_await(class_name):
        found_card = card_manager.find_card_in_deck(class_name)
        if found_card:
            # TODO: Особый случай - карта в await, нужна специальная логика смены цикла
            card_manager.play_known_card(class_name)  # временно используем обычную логику

    # Если карта не найдена в card_manager, ищем в all_cards для получения spell_life_time
    if not found_card:
        found_card = _find_card_by_class_name(class_name, all_cards)

    return found_card


def _find_card_by_class_name(class_name: str, all_cards: List[Card]) -> Optional[Card]:
    """
    Вспомогательная функция для поиска карты заклинания по class_name.

    Args:
        class_name: class_name для поиска
        all_cards: список всех карт

    Returns:
        Card если найдена, None иначе
    """
    for card in all_cards:
        if card.class_name == class_name:
            return card
    return None


def _find_card_by_spell_my_hand_class_name(class_name: str, all_cards: List[Card]) -> Optional[Card]:
    """
    Вспомогательная функция для поиска карты заклинания по spell_my_hand_class_name.

    Args:
        class_name: class_name для поиска
        all_cards: список всех карт

    Returns:
        Card если найдена, None иначе
    """
    for card in all_cards:
        if card.spell_my_hand_class_name == class_name:
            return card
    return None


def process_spell_detections(
    all_detections: List[Dict[str, Any]],
    spell_dict_hand: Dict[str, List[int]],
    spell_dict_our: Dict[str, List[float]],
    spell_dict_enemy: Dict[str, List[float]],
    card_manager: CardManager,
    current_time: float,
    all_cards: List[Card]
) -> float:
    """
    Главная функция обработки заклинаний.
    Координирует все процессы: обновление spell_dict_hand, проверку таймаутов, обработку детекций.

    Args:
        all_detections: все детекции текущего кадра
        spell_dict_hand: словарь НАШИХ заклинаний в руке (скользящее окно)
        spell_dict_our: словарь списков таймаутов НАШИХ активных заклинаний
        spell_dict_enemy: словарь списков таймаутов ВРАЖЕСКИХ активных заклинаний
        card_manager: менеджер карт противника
        current_time: текущая временная метка
        all_cards: список всех карт

    Returns:
        float: суммарный потраченный эликсир в текущей итерации

    Логика (последовательность):
        1. Очистка хвостов spell_dict_hand (скользящее окно)
        2. Обновление spell_dict_hand (детекция НАШИХ заклинаний в руке)
        3. Проверка и очистка spell_dict_our (истекшие таймауты НАШИХ заклинаний)
        4. Проверка и очистка spell_dict_enemy (истекшие таймауты ВРАЖЕСКИХ заклинаний)
        5. Обработка детекций заклинаний на ПОЛЕ (по счетчикам):
           - Подсчитываем детекции каждого заклинания
           - Сравниваем с известными (our + enemy)
           - Если detected > known → обрабатываем новые вражеские
           - Накапливаем elixir_spent
        6. Возврат суммарного elixir_spent

    Три словаря заклинаний:
        spell_dict_hand:  {"ZE_rage": [1,0,0,0], ...}           - отслеживание НАШЕЙ руки
        spell_dict_our:   {"SE_rage": [timeout_1, ...], ...}    - НАШИ активные заклинания (до 2)
        spell_dict_enemy: {"SE_rage": [timeout_1, ...], ...}    - ВРАЖЕСКИЕ активные заклинания (до 2)

    Поддержка зеркальных режимов:
        Игровой лимит: максимум 2 одинаковых заклинания на поле одновременно.
        Счетчики позволяют корректно различать НАШИ и ВРАЖЕСКИЕ заклинания.
    """
    # 1. Очистка хвостов spell_dict_hand (скользящее окно)
    cleanup_spell_dict_hand(spell_dict_hand)

    # 2. Обновление spell_dict_hand (НАШИ заклинания в руке)
    update_spell_dict_hand(all_detections, spell_dict_hand, spell_dict_our, current_time, all_cards)

    # 3. Проверка и очистка spell_dict_our (истекшие таймауты НАШИХ заклинаний)
    check_spell_dict_timeout(spell_dict_our, current_time)

    # 4. Проверка и очистка spell_dict_enemy (истекшие таймауты ВРАЖЕСКИХ заклинаний)
    check_spell_dict_timeout(spell_dict_enemy, current_time)

    # 5. Обработка детекций заклинаний на ПОЛЕ (по счетчикам)
    elixir_spent_total = 0.0

    # 5.1. Подсчитываем детекции каждого заклинания в текущем кадре
    detected_spells_count: Dict[str, int] = {}

    for detection in all_detections:
        class_name = detection.get('class_name', '')
        # Заклинания на поле боя имеют class_name начинающийся с "S" (SC, SE, SL, SR)
        if class_name and class_name.startswith('S') and len(class_name) > 1:
            # Проверяем что это действительно заклинание
            card = _find_card_by_class_name(class_name, all_cards)
            if card and card.spell:
                # Увеличиваем счетчик детекций
                detected_spells_count[class_name] = detected_spells_count.get(class_name, 0) + 1

    # 5.2. Обрабатываем каждое уникальное заклинание
    for class_name, detected_count in detected_spells_count.items():
        # Количество известных заклинаний (НАШИ + ВРАЖЕСКИЕ)
        our_count = len(spell_dict_our.get(class_name, []))
        enemy_count = len(spell_dict_enemy.get(class_name, []))
        total_known = our_count + enemy_count

        # Если детектировано больше чем известно → это новые вражеские заклинания
        if detected_count > total_known:
            new_enemy_count = detected_count - total_known

            # Обрабатываем ОДНО новое вражеское заклинание (запуск цикла карт, списание элека)
            # Даже если new_enemy_count > 1 (лаг), обрабатываем как одно (игровая механика)
            found_card = _process_new_enemy_spell(class_name, card_manager, all_cards)

            # Если карта найдена, списываем элек и добавляем таймауты
            if found_card:
                # Списываем эликсир ОДИН раз
                elixir_spent_total += found_card.elixir

                # Добавляем таймауты для ВСЕХ новых вражеских заклинаний (для корректности счетчиков)
                if found_card.spell_life_time:
                    if class_name not in spell_dict_enemy:
                        spell_dict_enemy[class_name] = []

                    # Добавляем new_enemy_count таймаутов
                    for _ in range(new_enemy_count):
                        timeout_end = current_time + found_card.spell_life_time
                        spell_dict_enemy[class_name].append(timeout_end)

    # 6. Возврат суммарного elixir_spent
    return elixir_spent_total
