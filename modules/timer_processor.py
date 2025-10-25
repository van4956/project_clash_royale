"""
Модуль для обработки красных таймеров (_timer_red).
Красные таймеры - основной сигнал размещения карт противника (юниты, здания).
"""

import logging

# Настраиваем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)

from typing import List, Tuple, Optional, Dict, Any
from collections import deque
from modules.classes import TimerObject, Card
from modules.functions import iou_box, cnt_box_timer, group_box_lvl, group_class_name, boxtimer_to_boxzone
from modules.card_manager import CardManager

Box = Tuple[float, float, float, float]  # (x1, y1, x2, y2)


def cleanup_timers(timer_list: List[TimerObject]) -> None:
    """
    Удаляет последний элемент из всех timer_obj в timer_list.
    Это "скользящее окно" - при каждой итерации удаляем самый старый кадр.

    Args:
        timer_list: глобальный список всех активных timer_obj

    Логика:
        - Проходим по всем timer_obj
        - У каждого удаляем последний элемент (самый старый timer_screen)
        - Если timer_obj становится пустым, он будет удален позже в check_timer_conditions
    """
    for timer_obj in timer_list:
        timer_obj.del_last()


def create_timer_screen(
    box_timer: Box,
    all_detections: List[Dict[str, Any]],
    log_screen: deque
) -> Tuple[List, List[str]]:
    """
    Создает timer_screen из обнаруженного красного таймера.

    Структура timer_screen:
        [[box_timer], [box_zone], [[box_lvl], [box_lvl], ...], [class_name, class_name, ...]]

    Args:
        box_timer: координаты обнаруженного красного таймера (x1, y1, x2, y2)
        all_detections: все детекции текущего кадра (список словарей с 'class_name', 'box', 'conf')
        log_screen: последние 4 кадра для создания list_ignore

    Returns:
        Tuple:
            - timer_screen: [[box_timer], [box_zone], [[box_lvl], ...], [class_name, ...]]
            - list_ignore: список class_name которые были в зоне за последние 4 кадра (для исключения)

    Логика:
        1. Берем координаты box_timer
        2. Вычисляем box_zone (расширенная зона отслеживания)
        3. Ищем все красные уровни (_lvl_red) в box_zone → box_lvl_list
        4. Ищем все class_name персонажей в box_zone → class_name_list
        5. Ищем все class_name в box_zone в log_screen (последние 4 кадра) → list_ignore
    """

    # 1. Координаты таймера
    timer_box = [box_timer]

    # 2. Вычисляем расширенную зону отслеживания
    box_zone = boxtimer_to_boxzone(box_timer)
    zone_box = [box_zone]

    # 3. Ищем все красные уровни (_lvl_red) в box_zone
    box_lvl_list = []
    for detection in all_detections:
        if detection.get('class_name') == '_lvl_red':
            det_box = detection.get('box')
            if det_box and _is_box_in_zone(det_box, box_zone):
                box_lvl_list.append(det_box)

    # 4. Ищем все class_name персонажей в box_zone
    class_name_list = []
    for detection in all_detections:
        class_name = detection.get('class_name')
        # Исключаем служебные классы (начинающиеся с "_")
        if class_name and not class_name.startswith('_'):
            det_box = detection.get('box')
            if det_box and _is_box_in_zone(det_box, box_zone):
                class_name_list.append(class_name)

    # 5. Создаем list_ignore из log_screen (последние 4 кадра)
    list_ignore = []
    for frame in log_screen:
        frame_detections = frame.get('detections', [])
        for detection in frame_detections:
            class_name = detection.get('class_name')
            if class_name and not class_name.startswith('_'):
                det_box = detection.get('box')
                if det_box and _is_box_in_zone(det_box, box_zone):
                    if class_name not in list_ignore:
                        list_ignore.append(class_name)

    # 6. Формируем timer_screen
    timer_screen = [timer_box, zone_box, box_lvl_list, class_name_list]

    return timer_screen, list_ignore


def _is_box_in_zone(box: Box, zone: Box) -> bool:
    """
    Проверяет, находится ли бокс в заданной зоне (пересечение).

    Args:
        box: координаты проверяемого бокса (x1, y1, x2, y2)
        zone: координаты зоны (x1, y1, x2, y2)

    Returns:
        True если боксы пересекаются, False иначе
    """
    x1, y1, x2, y2 = box
    zx1, zy1, zx2, zy2 = zone

    # Проверка на пересечение прямоугольников
    # Не пересекаются если один полностью левее/правее/выше/ниже другого
    if x2 < zx1 or x1 > zx2:
        return False
    if y2 < zy1 or y1 > zy2:
        return False

    return True


def find_matching_timer_obj(
    timer_list: List[TimerObject],
    timer_screen: List,
    iou_threshold: float = 0.8
) -> Optional[TimerObject]:
    """
    Ищет существующий timer_obj, который соответствует новому timer_screen.

    Args:
        timer_list: глобальный список всех timer_obj
        timer_screen: новый созданный timer_screen: [[box_timer], [box_zone], [[box_lvl], ...], [class_name, ...]]
        iou_threshold: порог IoU для считания таймеров одинаковыми (по умолчанию 0.8)

    Returns:
        Найденный timer_obj или None если совпадений нет

    Логика:
        - Проходим по всем timer_obj в timer_list
        - В каждом timer_obj берем первый элемент (самый свежий timer_screen)
        - Извлекаем box_timer (первый элемент timer_screen[0])
        - Сравниваем с box_timer нового timer_screen через iou_box()
        - Если IoU >= iou_threshold → нашли совпадение
    """
    new_box_timer = timer_screen[0][0] if timer_screen[0] else None

    if not new_box_timer:
        return None

    for timer_obj in timer_list:
        # Ищем первый непустой timer_screen в timer_obj (идем сверху вниз)
        existing_box_timer = None
        for ts in timer_obj:
            if ts and ts[0]:  # timer_screen не пуст и box_timer есть
                existing_box_timer = ts[0][0]
                break

        if not existing_box_timer:
            continue

        # Сравниваем box_timer через iou_box
        similarity = iou_box(existing_box_timer, new_box_timer)

        if similarity >= iou_threshold:
            return timer_obj

    return None


def create_new_timer_obj(
    timer_screen: List,
    timestamp: float,
    list_ignore: List[str]
) -> TimerObject:
    """
    Создает новый timer_obj из timer_screen.

    Args:
        timer_screen: созданный timer_screen
        timestamp: временная метка обнаружения
        list_ignore: список class_name для игнорирования

    Returns:
        Новый TimerObject с 6 timer_screen (1 заполненный + 5 пустых)

    Логика:
        - Помещаем timer_screen на первую позицию
        - Создаем 5 пустых timer_screen: [[], [], [], []]
        - Заполняем атрибуты: first_screen, last_screen, list_ignore
    """
    # Создаем 5 пустых timer_screen
    empty_screens = [[[], [], [], []] for _ in range(5)]

    # Формируем timer_obj: [timer_screen] + 5 пустых
    timer_obj_data = [timer_screen] + empty_screens

    # Создаем TimerObject с атрибутами
    timer_obj = TimerObject()
    timer_obj.extend(timer_obj_data)  # Заполняем данными как список
    timer_obj.first_screen = timestamp
    timer_obj.last_screen = timestamp
    timer_obj.list_ignore = list_ignore if list_ignore else []

    return timer_obj


def update_timer_obj(
    timer_obj: TimerObject,
    timer_screen: List,
    timestamp: float
) -> None:
    """
    Обновляет существующий timer_obj новым timer_screen.

    Args:
        timer_obj: существующий timer_obj
        timer_screen: новый timer_screen для добавления
        timestamp: временная метка обнаружения

    Логика:
        - Вставляем timer_screen на первую позицию (метод add_full)
        - Обновляем last_screen
    """
    timer_obj.add_full(timer_screen)
    timer_obj.last_screen = timestamp


def fill_missing_timer_screen(
    timer_obj: TimerObject,
    all_detections: List[Dict[str, Any]],
    timestamp: float
) -> None:
    """
    Заполняет пустой timer_screen когда в timer_obj 5 элементов.

    Args:
        timer_obj: timer_obj с 5 элементами
        all_detections: все детекции текущего кадра
        timestamp: временная метка

    Логика:
        - Создаем пустой timer_screen: [[], [], [], []]
        - Копируем box_zone из первого элемента timer_obj
        - Ищем все красные уровни (_lvl_red) в box_zone
        - Ищем все class_name в box_zone
        - Добавляем timer_screen в начало timer_obj
        - Обновляем last_screen
    """
    # Берем box_zone из первого timer_screen
    box_zone = None
    if len(timer_obj) > 0 and timer_obj[0] and len(timer_obj[0]) > 1:
        box_zone = timer_obj[0][1][0] if timer_obj[0][1] else None

    if not box_zone:
        # Если box_zone нет, создаем полностью пустой timer_screen
        empty_screen = [[], [], [], []]
        timer_obj.add_full(empty_screen)
        timer_obj.last_screen = timestamp
        return

    # Ищем красные уровни в box_zone
    box_lvl_list = []
    for detection in all_detections:
        if detection.get('class_name') == '_lvl_red':
            det_box = detection.get('box')
            if det_box and _is_box_in_zone(det_box, box_zone):
                box_lvl_list.append(det_box)

    # Ищем class_name в box_zone
    class_name_list = []
    for detection in all_detections:
        class_name = detection.get('class_name')
        if class_name and not class_name.startswith('_'):
            det_box = detection.get('box')
            if det_box and _is_box_in_zone(det_box, box_zone):
                class_name_list.append(class_name)

    # Создаем timer_screen: box_timer пуст, box_zone есть, box_lvl и class_name найдены
    timer_screen = [[], [box_zone], box_lvl_list, class_name_list]

    # Добавляем в начало timer_obj
    timer_obj.add_full(timer_screen)
    timer_obj.last_screen = timestamp


def check_timer_conditions(
    timer_obj: TimerObject,
    card_manager: CardManager
) -> Optional[Card]:
    """
    Проверяет условия подтверждения timer_obj и определяет сыгранную карту.

    Args:
        timer_obj: проверяемый timer_obj (должен содержать 6 timer_screen)
        card_manager: менеджер карт для поиска карт в колоде/руке/ожидании

    Returns:
        Card если карта определена, None если условия не выполнены

    Логика (процесс проверки условий):
        Усл.1 - подсчет box_timer (cnt_box_timer)
            0 → удаляем timer_obj (возвращаем None, удаление в вызывающей функции)
            1-2 → пропускаем (возвращаем None)
            3-6 → продолжаем проверку

        Усл.2 - подсчет и группировка box_lvl (group_box_lvl)
            Ищем группы красных уровней с подтверждением >= 3

        Усл.3 - подсчет и группировка class_name (group_class_name)
            Ищем class_name с подтверждением >= 3
            Если class_name == "_bomb" → удаляем timer_obj (бомбы игнорируем)

        Если усл.2 и усл.3 выполнены:
            - Удаляем из group_class_name все class_name из timer_obj.list_ignore
            - Ищем совпадение в hand_cards
            - Если не нашли и есть card_random → ищем в deck_cards
            - Если не нашли → ищем в await_cards (сбой цикла)
            - Если нашли → возвращаем карту
    """

    # Усл.1: Подсчет box_timer
    timer_count = cnt_box_timer(timer_obj)

    if timer_count == 0:
        # Таймер не виден 1.5 сек → удаляем timer_obj
        return None

    if timer_count in [1, 2]:
        # Недостаточно подтверждений → пропускаем
        return None

    # timer_count >= 3 → продолжаем проверку

    # Усл.2: Подсчет и группировка box_lvl
    lvl_groups_count = group_box_lvl(timer_obj, threshold=3, iou_threshold=0.8)

    # Усл.3: Подсчет и группировка class_name
    # Извлекаем все class_name из timer_obj
    all_class_names = []
    for timer_screen in timer_obj:
        if len(timer_screen) > 3 and timer_screen[3]:
            all_class_names.append(timer_screen[3])

    grouped_class_names = group_class_name(all_class_names, threshold=3)

    # Проверка на "_bomb" (бомбы игнорируем)
    if "_ bomb" in grouped_class_names:
        return None

    # Если усл.2 и усл.3 НЕ выполнены → пропускаем
    if lvl_groups_count == 0 or not grouped_class_names:
        return None

    # Усл.2 и усл.3 выполнены → определяем карту

    # Удаляем class_name из list_ignore
    ignore_list = timer_obj.list_ignore if timer_obj.list_ignore else []
    filtered_class_names = [
        cn for cn in grouped_class_names
        if cn not in ignore_list
    ]

    if not filtered_class_names:
        # Все class_name были в list_ignore → пропускаем
        return None

    # Ищем карту в hand_cards
    for class_name in filtered_class_names:
        if card_manager.is_card_in_hand(class_name):
            found_card = card_manager.find_card_in_deck(class_name)
            if found_card:
                return found_card

    # Если не нашли в hand_cards и есть card_random → ищем в deck_cards
    if card_manager.count_card_random_in_hand() > 0:
        for class_name in filtered_class_names:
            found_card = card_manager.find_card_in_deck(class_name)
            if found_card:
                return found_card

    # Если не нашли в deck_cards → ищем в await_cards (сбой цикла)
    for class_name in filtered_class_names:
        if card_manager.is_card_in_await(class_name):
            found_card = card_manager.find_card_in_deck(class_name)
            if found_card:
                # TODO: Особый случай - карта в await, нужна специальная логика смены цикла
                return found_card

    # Не нашли ни где → пропускаем (timer_obj самоуничтожится через 6 кадров)
    return None


def process_confirmed_timer(
    confirmed_card: Card,
    card_manager: CardManager,
    elixir_spent: List[float],
    evolution_dict_timer: Dict[float, str] | None = None
) -> None:
    """
    Обрабатывает подтвержденный таймер - запускает смену цикла карт и списывает эликсир.

    Args:
        confirmed_card: определенная карта противника
        card_manager: менеджер карт
        elixir_spent: список для накопления потраченного эликсира (mutable для изменения)
        evolution_dict_timer: словарь таймеров маркеров эволюции (опционально)

    Логика:
        1. Проверяем где карта: в hand_cards или в deck_cards
        2. Запускаем соответствующий метод card_manager (play_known_card или play_new_card)
        3. Передаем evolution_dict_timer для обработки эволюций
        4. Добавляем стоимость карты в elixir_spent
        5. (Анимация будет запускаться в overlay_dynamic.py - пока заглушка)
    """
    class_name = confirmed_card.class_name

    # Проверяем что class_name не None
    if not class_name:
        return

    # Проверяем где карта
    if card_manager.is_card_in_hand(class_name):
        # Карта в руке → известная карта
        card_manager.play_known_card(class_name, evolution_dict_timer)
    else:
        # Карта новая (из deck_cards)
        card_manager.play_new_card(class_name, evolution_dict_timer)

    # Списываем эликсир
    elixir_spent[0] += confirmed_card.elixir

    # TODO: Запустить анимацию смены карт в overlay_dynamic.py
    # TODO: Запустить анимацию изменения эликсира в overlay_dynamic.py


def process_timer_detections(
    log_screen: deque,
    timer_list: List[TimerObject],
    card_manager: CardManager,
    all_detections: List[Dict[str, Any]],
    timestamp: float,
    evolution_dict_timer: Dict[float, str] | None = None
) -> float:
    """
    Главная функция обработки красных таймеров.
    Координирует все процессы: создание, обновление, проверку timer_obj.

    Args:
        log_screen: последние 4 кадра с детекциями
        timer_list: глобальный список timer_obj (модифицируется)
        card_manager: менеджер карт противника
        all_detections: все детекции текущего кадра
        timestamp: временная метка текущего кадра
        evolution_dict_timer: словарь таймеров маркеров эволюции (опционально)

    Returns:
        float: суммарный потраченный эликсир в текущей итерации

    Логика (последовательность):
        1. Очистка хвостов (cleanup_timers)
        2. Обработка новых красных таймеров:
            - Создание timer_screen для каждого _timer_red
            - Поиск совпадений в timer_list
            - Создание новых или обновление существующих timer_obj
        3. Заполнение пустых timer_screen (когда в timer_obj 5 элементов)
        4. Проверка условий и обработка подтвержденных таймеров:
            - check_timer_conditions для всех timer_obj
            - process_confirmed_timer для найденных карт
            - Удаление обработанных timer_obj
        5. Возврат суммарного elixir_spent
    """

    # 1. Очистка хвостов (удаляем последний элемент у всех timer_obj)
    cleanup_timers(timer_list)

    # 2. Обработка новых красных таймеров
    red_timers = []
    for detection in all_detections:
        if detection.get('class_name') == '_ timer red':
            box = detection.get('box')
            if box:
                red_timers.append(box)

    # Для каждого красного таймера создаем или обновляем timer_obj
    for box_timer in red_timers:
        # Создаем timer_screen
        timer_screen, list_ignore = create_timer_screen(box_timer, all_detections, log_screen)

        # Ищем существующий timer_obj
        existing_timer = find_matching_timer_obj(timer_list, timer_screen, iou_threshold=0.7)

        if existing_timer:
            # Обновляем существующий timer_obj
            update_timer_obj(existing_timer, timer_screen, timestamp)
        else:
            # Создаем новый timer_obj
            new_timer_obj = create_new_timer_obj(timer_screen, timestamp, list_ignore)
            timer_list.append(new_timer_obj)

    # 3. Заполнение пустых timer_screen (когда в timer_obj 5 элементов)
    for timer_obj in timer_list:
        if len(timer_obj) == 5:
            fill_missing_timer_screen(timer_obj, all_detections, timestamp)

    # 4. Проверка условий и обработка подтвержденных таймеров
    elixir_spent_total = [0.0]  # Используем список для mutable объекта
    timers_to_remove = []

    for timer_obj in timer_list:
        # Проверяем только timer_obj с 6 элементами
        if len(timer_obj) != 6:
            continue

        # Проверяем условия и определяем карту
        confirmed_card = check_timer_conditions(timer_obj, card_manager)

        if confirmed_card:
            # Обрабатываем подтвержденный таймер
            process_confirmed_timer(confirmed_card, card_manager, elixir_spent_total, evolution_dict_timer)

            # Помечаем timer_obj для удаления
            timers_to_remove.append(timer_obj)

    # Удаляем обработанные timer_obj
    for timer_obj in timers_to_remove:
        timer_list.remove(timer_obj)

    # Удаляем timer_obj с timer_count == 0 (не видны 1.5 сек)
    timers_to_remove_zero = []
    for timer_obj in timer_list:
        if len(timer_obj) == 6:
            timer_count = cnt_box_timer(timer_obj)
            if timer_count == 0:
                timers_to_remove_zero.append(timer_obj)

    for timer_obj in timers_to_remove_zero:
        timer_list.remove(timer_obj)

    return elixir_spent_total[0]
