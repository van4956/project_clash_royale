"""
Модуль для обработки заклинаний (Spells).
Отыгрыш заклинаний НЕ маркируется таймерами.
Определение происходит по детекции эффекта заклинания на поле и сопоставлению с нашими заклинаниями.
"""

from typing import Dict, List, Any, Optional
from modules.classes import Card
from modules.card_manager import CardManager


def cleanup_spell_dict_list(spell_dict_list: Dict[str, List[int]]) -> None:
    """
    Очистка хвостов spell_dict_list - сдвиг скользящего окна.
    Удаляет последний элемент (самый старый) из каждого списка.

    Args:
        spell_dict_list: словарь наших заклинаний в руке
                        {"class_name": [1,0,0,0], "class_name": [1,1,1,1], ...}

    Логика:
        - Проходим по всем class_name в spell_dict_list
        - У каждого списка удаляем последний элемент (pop)
        - Скользящее окно: [1,0,0,0] → [1,0,0] (после pop)
    """
    for class_name in spell_dict_list:
        if spell_dict_list[class_name]:  # если список не пуст
            spell_dict_list[class_name].pop()  # удаляем последний элемент


def update_spell_dict_list(
    all_detections: List[Dict[str, Any]],
    spell_dict_list: Dict[str, List[int]],
    spell_dict_time: Dict[str, float],
    current_time: float,
    all_cards: List[Card]
) -> None:
    """
    Обновляет список НАШИХ заклинаний в НАШЕЙ руке (spell_dict_list).

    Args:
        all_detections: все детекции текущего кадра
        spell_dict_list: словарь НАШИХ заклинаний {"class_name": [1,0,0,0], ...}
        spell_dict_time: словарь таймаутов наших заклинаний {"class_name": timeout_end, ...}
        current_time: текущая временная метка
        all_cards: список всех карт для получения spell_life_time

    Логика:
        1. Ищем детекции заклинаний в НАШЕЙ руке (class_name начинается с "Z", особый нейминг для карт в НАШЕЙ руке)
        2. Для каждого найденного заклинания:
           - Если class_name есть в spell_dict_list → добавляем 1 в начало списка
           - Если class_name НЕТ в spell_dict_list → создаем новую запись [1,0,0,0]
        3. Для заклинаний которые НЕ детектированы:
           - Добавляем 0 в начало списка
        4. Проверяем на исчезновение (список стал [0,0,0,0]):
           - Переносим в spell_dict_time с таймаутом

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

    # Обновляем spell_dict_list
    # Для каждого известного заклинания добавляем 1 или 0 в начало списка
    for class_name in list(spell_dict_list.keys()):
        if class_name in detected_spells:
            # Заклинание детектировано → добавляем 1 в начало
            spell_dict_list[class_name].insert(0, 1)
        else:
            # Заклинание НЕ детектировано → добавляем 0 в начало
            spell_dict_list[class_name].insert(0, 0)

        # Проверяем на исчезновение [0,0,0,0]
        if spell_dict_list[class_name] == [0, 0, 0, 0]:
            # Заклинание исчезло из руки → переносим в spell_dict_time
            # Находим карту для получения spell_life_time
            card = _find_card_by_spell_my_hand_class_name(class_name, all_cards)
            # Если карта найдена и у нее есть время отыгрывания заклинания, то записываем в словарь spell_dict_time
            if card and card.spell_life_time:
                # Таймаут = текущее время + время отыгрывания заклинания
                timeout_end = current_time + card.spell_life_time
                # Записываем в словарь spell_dict_time по основному class_name
                if card.class_name:
                    card_class_name = card.class_name
                    spell_dict_time[card_class_name] = timeout_end

            # Удаляем из spell_dict_list НАШЕ заклинание
            del spell_dict_list[class_name]

    # Добавляем новые заклинания в spell_dict_list
    for class_name in detected_spells:
        if class_name not in spell_dict_list:
            # Новое заклинание в руке → создаем запись [1,0,0,0]
            spell_dict_list[class_name] = [1, 0, 0, 0]


def check_spell_dict_time(
    spell_dict_time: Dict[str, float],
    current_time: float
) -> None:
    """
    Проверяет таймауты в spell_dict_time и удаляет истекшие записи.

    Args:
        spell_dict_time: словарь таймаутов {"class_name": timeout_end, ...}
        current_time: текущая временная метка

    Логика:
        - Проходим по всем записям в spell_dict_time
        - Если current_time >= timeout_end → таймаут истек → удаляем запись
        - Это означает что наше заклинание уже отыгралось на поле
    """
    # Создаем список для удаления (нельзя изменять словарь во время итерации)
    to_remove = []

    for class_name, timeout_end in spell_dict_time.items():
        if current_time >= timeout_end:
            # Таймаут истек → помечаем для удаления
            to_remove.append(class_name)

    # Удаляем истекшие записи
    for class_name in to_remove:
        del spell_dict_time[class_name]


def process_spell_detection(
    class_name: str,
    spell_dict_time: Dict[str, float],
    card_manager: CardManager,
    elixir_spent: List[float]
) -> bool:
    """
    Обрабатывает детекцию заклинания на поле боя.

    Args:
        class_name: class_name детектированного заклинания на поле
        spell_dict_time: словарь таймаутов наших заклинаний
        card_manager: менеджер карт противника
        elixir_spent: список для накопления потраченного эликсира

    Returns:
        bool: True если это заклинание противника (обработано), False если наше (игнорируем)

    Логика:
        1. Проверяем spell_dict_time - есть ли там это заклинание?
        2. Если ДА → это НАШЕ заклинание → возвращаем False (НЕ списываем элек противника)
        3. Если НЕТ → это заклинание ПРОТИВНИКА:
           - Ищем карту в hand_cards или deck_cards
           - Запускаем цикл карт (play_known_card или play_new_card)
           - Списываем эликсир
           - Возвращаем True

    Примечание:
        НЕ удаляем заклинание из spell_dict_time (самоочистка по таймауту).
        Если детектируем два одинаковых заклинания подряд, второе будет обработано как вражеское.
    """
    # Проверяем spell_dict_time
    if class_name in spell_dict_time:
        # Это НАШЕ заклинание → игнорируем
        return False

    # Это заклинание ПРОТИВНИКА → обрабатываем

    # Ищем карту в hand_cards
    if card_manager.is_card_in_hand(class_name):
        # Карта в руке → известная карта
        found_card = card_manager.find_card_in_deck(class_name)
        if found_card:
            card_manager.play_known_card(class_name)
            elixir_spent[0] += found_card.elixir
            return True

    # Если не нашли в hand_cards и есть card_random → ищем в deck_cards
    if card_manager.count_card_random_in_hand() > 0:
        found_card = card_manager.find_card_in_deck(class_name)
        if found_card:
            card_manager.play_new_card(class_name)
            elixir_spent[0] += found_card.elixir
            return True

    # Если не нашли в deck_cards → ищем в await_cards (сбой цикла)
    if card_manager.is_card_in_await(class_name):
        found_card = card_manager.find_card_in_deck(class_name)
        if found_card:
            # TODO: Особый случай - карта в await, нужна специальная логика смены цикла
            card_manager.play_known_card(class_name)  # временно используем обычную логику
            elixir_spent[0] += found_card.elixir
            return True

    # Карта не найдена нигде → не обрабатываем
    return False


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
    spell_dict_list: Dict[str, List[int]],
    spell_dict_time: Dict[str, float],
    card_manager: CardManager,
    current_time: float,
    all_cards: List[Card]
) -> float:
    """
    Главная функция обработки заклинаний.
    Координирует все процессы: обновление spell_dict_list, проверку таймаутов, обработку детекций.

    Args:
        all_detections: все детекции текущего кадра
        spell_dict_list: словарь наших заклинаний в руке
        spell_dict_time: словарь таймаутов наших заклинаний
        card_manager: менеджер карт противника
        current_time: текущая временная метка
        all_cards: список всех карт

    Returns:
        float: суммарный потраченный эликсир в текущей итерации

    Логика (последовательность):
        1. Очистка хвостов spell_dict_list (скользящее окно)
        2. Обновление spell_dict_list (детекция НАШИХ заклинаний в руке)
        3. Проверка и очистка spell_dict_time (истекшие таймауты)
        4. Обработка детекций заклинаний на ПОЛЕ:
           - Ищем эффекты заклинаний в all_detections
           - Для каждого вызываем process_spell_detection()
           - Накапливаем elixir_spent
        5. Возврат суммарного elixir_spent
    """
    # 1. Очистка хвостов spell_dict_list (скользящее окно)
    cleanup_spell_dict_list(spell_dict_list)

    # 2. Обновление spell_dict_list (НАШИ заклинания в руке)
    update_spell_dict_list(all_detections, spell_dict_list, spell_dict_time, current_time, all_cards)

    # 3. Проверка и очистка spell_dict_time (истекшие таймауты)
    check_spell_dict_time(spell_dict_time, current_time)

    # 4. Обработка детекций заклинаний на ПОЛЕ
    elixir_spent_total = [0.0]

    # Ищем заклинания в детекциях
    for detection in all_detections:
        class_name = detection.get('class_name', '')
        # Заклинания на поле боя имеют class_name начинающийся с "S" (SC, SE, SL, SR)
        if class_name and class_name.startswith('S') and len(class_name) > 1:
            # Определяем карту по ее class_name
            card = _find_card_by_class_name(class_name, all_cards)
            if card and card.spell:
                # Обрабатываем детекцию заклинания
                process_spell_detection(class_name, spell_dict_time, card_manager, elixir_spent_total)

    return elixir_spent_total[0]
