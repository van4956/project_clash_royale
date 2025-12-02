"""
Модуль для обработки красных таймеров (_ timer red).
Красные таймеры - основной сигнал размещения карт противника (юниты, здания).
"""

import logging

# Настраиваем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)

from typing import List, Tuple, Optional, Dict, Any
from collections import deque, Counter, defaultdict
import math

from modules.classes import TimerObject, Card
from modules.card_manager import CardManager
from config import get_roi_bounds



# ==== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====

Box = Tuple[float, float, float, float]  # (x1, y1, x2, y2)

def iou_box(
    box_a: Box,
    box_b: Box,
    alpha: float = 1,     # значимость IoU в общем скоре (пока что 1, потом скорректирую)
    sigma: float = 0.9    # не чувствительность к смещению центров
) -> float:
    """
    Функция вычисляет композитный скор схожести двух боксов:
    score = alpha * IoU + (1 - alpha) * exp( - (d / (sigma * D))^2 )

    box_a, box_b: (x1, y1, x2, y2) с произвольным порядком (нормализуем внутри)
    alpha:   значимость IoU в общем скоре - чем больше alpha, тем больше вес IoU, и тем меньше роль расстояния центров.
    sigma:   устойчивость к смещению центров - при высоком sigma = 1 расстояние не учитывается в общем скоре.

    Возвращает число в [0, 1]. Чем выше — тем «похожее» два бокса.
    """

    # --- нормализация координат (гарантируем x1<=x2, y1<=y2)
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ax1, ax2 = min(ax1, ax2), max(ax1, ax2)
    ay1, ay2 = min(ay1, ay2), max(ay1, ay2)
    bx1, bx2 = min(bx1, bx2), max(bx1, bx2)
    by1, by2 = min(by1, by2), max(by1, by2)

    # --- площади
    aw = max(0.0, ax2 - ax1)
    ah = max(0.0, ay2 - ay1)
    bw = max(0.0, bx2 - bx1)
    bh = max(0.0, by2 - by1)
    area_a = aw * ah
    area_b = bw * bh

    # Если хоть один бокс вырожден (площадь = 0) —> IoU = 0
    if area_a <= 0.0 or area_b <= 0.0:
        iou = 0.0
    else:
        # --- пересечение
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        inter = iw * ih

        # --- объединение
        union = area_a + area_b - inter
        iou = inter / union if union > 0.0 else 0.0

    # --- дистанция между центрами
    acx = (ax1 + ax2) * 0.5
    acy = (ay1 + ay2) * 0.5
    bcx = (bx1 + bx2) * 0.5
    bcy = (by1 + by2) * 0.5
    d = math.hypot(acx - bcx, acy - bcy)

    # --- диагональ объединяющего прямоугольника (масштаб нормализации)
    ux1 = min(ax1, bx1)
    uy1 = min(ay1, by1)
    ux2 = max(ax2, bx2)
    uy2 = max(ay2, by2)
    uw = max(0.0, ux2 - ux1)
    uh = max(0.0, uy2 - uy1)
    D = math.hypot(uw, uh)

    # Если боксы совпадают по центру или D=0 (патологический случай) — центр-терм = 1
    if D <= 0.0 or sigma <= 0.0:
        center_term = 1.0
    else:
        norm = d / (sigma * D)
        center_term = math.exp(-(norm * norm))

    # --- финальный скор
    score = alpha * iou + (1.0 - alpha) * center_term

    # численно ограничим в [0,1] на всякий
    if score < 0.0:
        score = 0.0
    elif score > 1.0:
        score = 1.0

    return score



def cnt_box_timer(timer_obj: List[List[List[int]]]) -> int:
    '''
    Подсчитывает количество box_timer (первый элемент timer_screen) в timer_obj.
    Принимает объект timer_obj, состоящий из 6 timer_screen.
    Возвращает число,количество box_timer.
    '''
    x = sum(1 for timer_screen in timer_obj if timer_screen[0])

    return x



def group_class_name(rows: List[List[str]], threshold: int = 3) -> List[str]:  # TODO: по умолчанию 3 - правильно
    """
    Принимает список строк, состоящих из перечня class_name, и пороговое значение threshold.

    Берём элемент в первой строке и идём вниз, вырезая совпадения
    Новая итерация — берём первый любой элемент и снова вниз
    Собираем все группы (cls, size), сортируем по size убыв., фильтруем по threshold,
    возвращаем список class_name

    Возвращает список class_name, у которых после группировки получилось >=threshold
    """
    # 1) построчные счётчики
    per_row = [Counter(row) for row in rows]

    # 2) группируем построчные количества по классам
    by_class: defaultdict[str, List[int]] = defaultdict(list)

    # Собираем все классы, которые встречались хотя бы где-то (множество)
    all_classes = set()
    for rc in per_row:
        all_classes.update(rc.keys())

    for cls in all_classes:
        # Считаем количество классов в каждой строке per_row
        counts = [rc.get(cls, 0) for rc in per_row]
        if sum(counts) == 0:
            continue

        # 3) Формируем группы для этого класса (cls)
        while True:
            # Находим индексы строк, где остались элементы
            pos_idx = [i for i, v in enumerate(counts) if v > 0]
            if not pos_idx:
                break
            # Размер группы = количество строк с положительным остатком
            group_size = len(pos_idx)
            by_class[cls].append(group_size)
            # Вычитаем по одному из всех строк, где ещё оставались элементы
            for i in pos_idx:
                counts[i] -= 1

    # 4) Соберём все группы (class_name, size)
    grouped: List[Tuple[str, int]] = []
    for cls, sizes in by_class.items():
        for s in sizes:
            grouped.append((cls, s))

    # 5) сортировка по размеру группы убыв. (детерминированный вывод, для тестов)
    grouped.sort(key=lambda x: (-x[1], x[0]))

    # 6) фильтр по порогу и возврат class_name
    result = [cls for cls, size in grouped if size >= threshold]
    return result



def boxtimer_to_boxzone(box_timer: Box) -> Box:
    """
    Преобразует координаты бокса таймера в расширенную зону отслеживания.

    Логика расширения:
    - Влево и вправо на 2 ширины бокса таймера
    - Вверх от верхней границы на 2 высоты бокса таймера
    - Нижняя граница остается на месте
    - Ограничение границами ROI (не выходим за пределы области детекции)

    Args:
        box_timer: (x1, y1, x2, y2) координаты бокса таймера

    Returns:
        box_zone: (x1, y1, x2, y2) расширенная зона отслеживания (ограниченная ROI)

    Пример:
        box_timer = (100, 100, 120, 110)  # ширина=20, высота=10
        box_zone = (60, 100, 160, 130)    # x1-40, y1, x2+40, y2+20 (если в пределах ROI)

    Обоснование ограничения ROI:
        Если таймер находится у края ROI, расширенная зона может выйти за границы.
        Модель детекции работает только внутри ROI, поэтому за пределами детекций нет.
        Ограничение box_zone границами ROI обеспечивает корректность поиска box_lvl и class_name.
    """
    # x1, y1, x2, y2 = box_timer
    x1, y1, x2, y2 = int(box_timer[0]), int(box_timer[1]), int(box_timer[2]), int(box_timer[3]) # TODO: вернуть после тестирования

    # Нормализация координат (на случай если x1>x2 или y1>y2)
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)

    # Вычисляем размеры бокса таймера
    width = x2 - x1   # ширина (l)
    height = y2 - y1  # высота (h)

    # Создаем расширенную зону
    zone_x1 = x1 - 2 * width   # влево на 2 ширины
    zone_y1 = y1
    zone_x2 = x2 + 2 * width   # вправо на 2 ширины
    zone_y2 = y2 + 2 * height  # вверх от верхней границы на 2 высоты

    # Получаем границы ROI из конфигурации
    roi_x_min, roi_y_min, roi_x_max, roi_y_max = get_roi_bounds()

    # Ограничиваем box_zone границами ROI
    zone_x1 = max(roi_x_min, zone_x1)  # слева: не выходим за левую границу ROI
    zone_y1 = max(roi_y_min, zone_y1)  # снизу: не выходим за нижнюю границу ROI
    zone_x2 = min(roi_x_max, zone_x2)  # справа: не выходим за правую границу ROI
    zone_y2 = min(roi_y_max, zone_y2)  # сверху: не выходим за верхнюю границу ROI

    return (zone_x1, zone_y1, zone_x2, zone_y2)



def group_box_lvl(timer_obj: List[List], threshold: int = 3, iou_threshold: float = 0.7) -> int:  # TODO: по умолчанию 3 - правильно
    """
    Группирует box_lvl из timer_obj по пересечению их координат (IoU).

    Принимает timer_obj (список из 6 timer_screen).
    Каждый timer_screen имеет структуру: [[box_timer], [box_zone], [[box_lvl], [box_lvl], ...], [class_name, ...]]
    Извлекает все box_lvl (timer_screen[2]) из всех timer_screen.
    Группирует боксы с IoU >= iou_threshold.

    Args:
        timer_obj: список из 6 timer_screen
        threshold: минимальное количество боксов в группе для учета (по умолчанию 3)
        iou_threshold: порог IoU для считания боксов одинаковыми (по умолчанию 0.7)

    Returns:
        int: количество групп, у которых размер >= threshold

    Пример:
        timer_obj = [
            [[box_timer], [box_zone], [[100,200,120,220], [102,198,118,222]], [class_name]],
            [[box_timer], [box_zone], [[101,201,119,221]], [class_name]],
            ...
        ]
        # Первые два бокса похожи (IoU > 0.7) → группа размера 3
        # Возвращает: 1 (одна группа с размером >= 3)
    """

    # 1) Собираем все box_lvl из всех timer_screen
    all_boxes = []
    for timer_screen in timer_obj:
        # timer_screen[2] - это список box_lvl
        if len(timer_screen) > 2 and timer_screen[2]:
            box_lvl_list = timer_screen[2]
            # Добавляем все боксы из этого timer_screen
            all_boxes.extend(box_lvl_list)

    # Если боксов нет - возвращаем 0
    if not all_boxes:
        return 0

    # 2) Группировка боксов по IoU похожести
    # Используем жадный алгоритм группировки
    groups = []  # список групп, каждая группа - список боксов
    used = [False] * len(all_boxes)  # отметки использованных боксов

    for i, box_i in enumerate(all_boxes):
        if used[i]:
            continue

        # Создаем новую группу с текущим боксом
        current_group = [box_i]
        used[i] = True

        # Ищем все похожие боксы
        for j, box_j in enumerate(all_boxes):
            if used[j]:
                continue

            # Проверяем IoU между box_i и box_j
            similarity = iou_box(box_i, box_j)

            if similarity >= iou_threshold:
                current_group.append(box_j)
                used[j] = True

        groups.append(current_group)

    # 3) Считаем количество групп с размером >= threshold
    valid_groups_count = sum(1 for group in groups if len(group) >= threshold)

    return valid_groups_count



# ==== ФУНКЦИИ ДЛЯ РАБОТЫ С timer_obj ====


def cleanup_timer_list(timer_list: List[TimerObject]) -> None:
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
        timer_obj.del_last_screen()


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
        3. Ищем все красные уровни (_ lvl red) в box_zone → timer_screen[2]
        4. Ищем все class_name персонажей в box_zone → timer_screen[3]
        5. Ищем все class_name в box_zone в log_screen (последние 4 кадра) → timer_obj.list_ignore
    """

    # 1. Координаты таймера
    # timer_box = [box_timer]
    box = [int(box_timer[0]), int(box_timer[1]), int(box_timer[2]), int(box_timer[3])] # TODO: вернуть после тестирования
    timer_box = [box]

    # 2. Вычисляем расширенную зону отслеживания
    box_zone = boxtimer_to_boxzone(box_timer)
    zone_box = [box_zone]

    # 3. Ищем все красные уровни (_ lvl red) в box_zone
    box_lvl_list = []
    for detection in all_detections:
        if detection.get('class_name') == '_ lvl red':
            det_box = detection.get('bbox')
            # det_box = [int(det_box[0]), int(det_box[1]), int(det_box[2]), int(det_box[3])] # TODO: вернуть после тестирования
            # print(f"det_box: {det_box}; box_zone: {box_zone}") # TODO: удалить после тестирования
            if det_box and _is_box_in_zone(det_box, box_zone):
                box_lvl_list.append(det_box)

    # 4. Ищем все class_name персонажей в box_zone
    class_name_list = []
    for detection in all_detections:
        class_name = detection.get('class_name')
        # Исключаем служебные классы (начинающиеся с "_")
        if class_name and not class_name.startswith('_') and not class_name.startswith('A') and not class_name.startswith('S'):
            det_box = detection.get('bbox')
            if det_box and _is_box_in_zone(det_box, box_zone):
                class_name_list.append(class_name)

    # 5. Создаем list_ignore из log_screen (последние 4 кадра)
    list_ignore = []
    for frame in log_screen:
        frame_detections = frame.get('detections', [])
        for detection in frame_detections:
            class_name = detection.get('class_name')
            if class_name and not class_name.startswith('_'):
                det_box = detection.get('bbox')
                if det_box and _is_box_in_zone(det_box, box_zone):
                    if class_name not in list_ignore:
                        list_ignore.append(class_name)

    # 6. Формируем timer_screen
    timer_screen = [timer_box, zone_box, box_lvl_list, class_name_list]

    # print(f"timer_screen: {timer_screen}; list_ignore: {list_ignore}") # TODO: удалить после тестирования

    return timer_screen, list_ignore


def _is_box_in_zone(box: Box, zone: Box) -> bool:
    """
    Проверяет, есть ли пересечение между боксом и зоной.

    Args:
        box: координаты проверяемого бокса (x1, y1, x2, y2)
        zone: координаты зоны (x1, y1, x2, y2)

    Returns:
        True если боксы пересекаются, иначе False
    """
    bx1, by1, bx2, by2 = box
    zx1, zy1, zx2, zy2 = zone

    # Проверка на пересечение прямоугольников
    if bx2 < zx1 or bx1 > zx2:
        return False

    if by2 < zy1 or by1 > zy2:
        return False

    return True


def find_timer_obj(
    timer_list: List[TimerObject],
    timer_screen: List,
    iou_threshold: float = 0.3
) -> Optional[TimerObject]:
    """
    Ищет существующий timer_obj, который соответствует новому timer_screen.

    Args:
        timer_list: глобальный список всех timer_obj
        timer_screen: новый созданный timer_screen: [[box_timer], [box_zone], [[box_lvl], ...], [class_name, ...]]
        iou_threshold: порог IoU для считания таймеров одинаковыми (по умолчанию 0.8)

    Returns:
        Найденный timer_obj если находит, или None если совпадений нет

    Логика:
        - Проходим по всем timer_obj в timer_list
        - В каждом timer_obj идем по всем timer_screen, берем первый элемент (timer_screen[0])
        - Ищем первый не пустой box_timer
        - Сравниваем с box_timer нового timer_screen через iou_box()
        - Если IoU >= iou_threshold → нашли совпадение
    """
    new_box_timer = timer_screen[0][0] if timer_screen[0] else None

    if not new_box_timer:
        return None

    for timer_obj in timer_list:
        # Ищем первый непустой timer_screen в timer_obj (идем сверху вниз)
        search_box_timer = None
        for ts in timer_obj:
            if ts and ts[0]:  # timer_screen не пуст и box_timer есть
                search_box_timer = ts[0][0]
                break

        if not search_box_timer:
            continue

        # Сравниваем box_timer через iou_box
        iou_value = iou_box(search_box_timer, new_box_timer, alpha=0.5, sigma=0.5)

        if iou_value >= iou_threshold:
            return timer_obj

    return None


def create_timer_obj(
    timer_screen: List,
    timestamp: float,
    list_ignore: List[str]
) -> TimerObject:
    """
    Создает новый timer_obj, на основе timer_screen.

    Args:
        timer_screen: созданный timer_screen
        timestamp: временная метка обнаружения
        list_ignore: список class_name для игнорирования

    Returns:
        Новый TimerObject с 6 timer_screen (1 заполненный + 5 пустых) и status="active"

    Логика:
        - Помещаем timer_screen на первую позицию
        - Создаем 5 пустых timer_screen: [[], [], [], []]
        - Заполняем атрибуты: time_first_screen, time_last_screen, list_ignore
        - status устанавливается по умолчанию в "active" (из dataclass)
    """
    # Создаем 5 пустых timer_screen
    empty_screens = [[[], [], [], []] for _ in range(5)]

    # Формируем timer_obj: [timer_screen] + 5 пустых
    timer_obj_data = [timer_screen] + empty_screens

    # Создаем TimerObject с атрибутами
    timer_obj = TimerObject()
    timer_obj.extend(timer_obj_data)  # Заполняем данными как список
    timer_obj.time_first_screen = timestamp
    timer_obj.time_last_screen = timestamp
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
        - Вставляем timer_screen на первую позицию (метод add_first_screen)
        - Обновляем last_screen
    """
    timer_obj.add_first_screen(timer_screen)
    timer_obj.last_screen = timestamp


def add_empty_timer_screen( # TODO: переписать, реализовать подсчет _lvl_red и class_name
    timer_obj: TimerObject,
    all_detections: List[Dict[str, Any]],
    timestamp: float
) -> None:
    """
    Добавляет в timer_obj пустой timer_screen,
    в котором определяется все _lvl_red и class_name по прошлому box_zone (из предыдущего не пустого timer_screen).

    Args:
        timer_obj: timer_obj с 5 элементами
        all_detections: все детекции текущего кадра
        timestamp: временная метка

    Логика:
        - Создаем пустой timer_screen: [[], [], [], []]
        - Копируем box_zone из первого не пустого элемента timer_obj
        - Ищем все красные уровни (_lvl_red) в box_zone
        - Ищем все class_name в box_zone
        - Добавляем timer_screen в начало timer_obj
        - Обновляем last_screen
    """
    # Берем box_zone из первого не пустого timer_screen
    box_zone = None
    for timer_screen in timer_obj:
        if timer_screen and len(timer_screen) > 1:
            box_zone = timer_screen[1][0]
            break

    if not box_zone:
        # Если box_zone все таки нет, создаем полностью пустой timer_screen
        empty_screen = [[], [], [], []]
        timer_obj.add_first_screen(empty_screen)
        timer_obj.time_last_screen = timestamp
        return

    # Ищем красные уровни в box_zone
    box_lvl_list = []
    # for detection in all_detections:
    #     if detection.get('class_name') == '_ lvl red':
    #         det_box = detection.get('bbox')
    #         if det_box and _is_box_in_zone(det_box, box_zone):
    #             box_lvl_list.append(det_box)

    # Ищем class_name в box_zone
    class_name_list = []
    # for detection in all_detections:
    #     class_name = detection.get('class_name')
    #     if class_name and not class_name.startswith('_'):
    #         det_box = detection.get('bbox')
    #         if det_box and _is_box_in_zone(det_box, box_zone):
    #             class_name_list.append(class_name)

    # Создаем timer_screen: box_timer пуст, box_zone есть, box_lvl и class_name найдены
    timer_screen = [[], [box_zone], box_lvl_list, class_name_list]

    # Добавляем в начало timer_obj
    timer_obj.add_first_screen(timer_screen)
    timer_obj.time_last_screen = timestamp


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
            0 → возвращаем None (timer_obj будет удален в process_timer_detections)
            1-2 → пропускаем (возвращаем None)
            3-6 → продолжаем проверку

        Усл.2 - подсчет и группировка box_lvl (group_box_lvl)
            Ищем группы красных уровней с подтверждением >= 3

        Усл.3 - подсчет и группировка class_name (group_class_name)
            Ищем class_name с подтверждением >= 3
            Если class_name == "_ bomb" → устанавливаем status="bomb", возвращаем None

        Если усл.2 и усл.3 выполнены:
            - Удаляем из group_class_name все class_name из timer_obj.list_ignore
            - Ищем совпадение в hand_cards
            - Если не нашли и есть card_random → ищем в deck_cards
            - Если не нашли → ищем в await_cards (сбой цикла)
            - Если нашли → возвращаем карту (status="done" устанавливается в process_timer_detections)
    """

    # Усл.1: Подсчет box_timer
    timer_count = cnt_box_timer(timer_obj)
    # print(f"timer_count: {timer_count}") # TODO: удалить после тестирования

    if timer_count == 0:
        # Таймер не виден 1.5 сек → timer_obj будет удален в process_timer_detections
        return None

    # if timer_count in [1, 2]:
    #     # Недостаточно подтверждений → пропускаем
    #     return None

    # timer_count >= 3 → продолжаем проверку

    # Усл.2: Подсчет и группировка box_lvl
    # lvl_groups_count = group_box_lvl(timer_obj, threshold=1, iou_threshold=0.8)  # TODO: вернуть threshold=3
    # print(f"lvl_groups_count: {lvl_groups_count}") # TODO: удалить после тестирования

    # Усл.3: Подсчет и группировка class_name
    # Извлекаем все class_name из timer_obj
    all_class_names = []
    for timer_screen in timer_obj:
        if len(timer_screen) > 3 and timer_screen[3]:
            all_class_names.append(timer_screen[3])

    grouped_class_names = group_class_name(all_class_names, threshold=1)  # TODO: вернуть threshold=3
    # print(f"grouped_class_names: {grouped_class_names}") # TODO: удалить после тестирования

    # Проверка на "_bomb" (бомбы игнорируем)
    if "_ bomb" in grouped_class_names:
        timer_obj.status = "bomb"
        return None

    # Если усл.2 и усл.3 НЕ выполнены → пропускаем
    # if lvl_groups_count == 0 or not grouped_class_names:
    #     return None

    # Усл.2 и усл.3 выполнены → определяем карту

    # Удаляем class_name из list_ignore
    # ignore_list = timer_obj.list_ignore if timer_obj.list_ignore else []
    # filtered_class_names = [
    #     cn for cn in grouped_class_names
    #     if cn not in ignore_list
    # ]
    filtered_class_names = grouped_class_names # TODO: вернуть ignore_list

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
    Обновляет card_manager и управляет жизненным циклом timer_obj через статусы.
    Возвращает суммарный потраченный эликсир в текущей итерации.

    Args:
        log_screen: последние 4 кадра с детекциями
        timer_list: глобальный список timer_obj (модифицируется)
        card_manager: менеджер карт противника
        all_detections: все детекции текущего кадра
        timestamp: временная метка текущего кадра
        evolution_dict_timer: словарь таймеров маркеров эволюции (опционально)

    Returns:
        float: суммарный потраченный эликсир в текущей итерации

    Последовательность:
        1. Обработка новых красных таймеров:
            - Создание timer_screen для каждого _ timer red
            - Поиск совпадений в timer_obj из timer_list
            - Создание новых (status="active") или обновление существующих timer_obj
        2. Добавление пустых timer_screen (для timer_obj с len < 6)
        3. Проверка условий и обработка подтвержденных таймеров:
            - Проверяем только timer_obj с 6 элементами и status="active"
            - check_timer_conditions: определяет карту или устанавливает status="bomb"
            - process_confirmed_timer: обрабатывает карту
            - Устанавливаем status="done" для обработанных timer_obj
        4. Удаление timer_obj (ЕДИНСТВЕННОЕ место удаления!):
            - Удаляем ТОЛЬКО когда cnt_box_timer == 0 (независимо от статуса)
        5. Возврат суммарного elixir_spent
    """

    # 1. Очистка хвостов (удаляем последний элемент у всех timer_obj)
    # cleanup_timer_list(timer_list) # TODO: лишнее удаление, так как в handler_processor.py уже есть очистка

    # 2. Обработка новых красных таймеров
    red_timers = []
    for detection in all_detections:
        if detection.get('class_name') == '_ timer red':
            box = detection.get('bbox')
            if box:
                red_timers.append(box)

    # Для каждого красного таймера создаем или обновляем timer_obj
    for box_timer in red_timers:
        # Создаем timer_screen
        timer_screen, list_ignore = create_timer_screen(box_timer, all_detections, log_screen)

        # Ищем существующий timer_obj
        current_timer = find_timer_obj(timer_list, timer_screen, iou_threshold=0.7)

        if current_timer:
            # Обновляем существующий timer_obj
            update_timer_obj(current_timer, timer_screen, timestamp)
        else:
            # Создаем новый timer_obj
            new_timer_obj = create_timer_obj(timer_screen, timestamp, list_ignore)
            timer_list.append(new_timer_obj)

    # 3. Добавление пустого timer_screen (когда в timer_obj меньше 6 элементов)
    for timer_obj in timer_list:
        if len(timer_obj) < 6:
            add_empty_timer_screen(timer_obj, all_detections, timestamp)

    # 4. Проверка условий и обработка подтвержденных таймеров
    elixir_spent_total = [0.0]  # Используем список для mutable объекта

    for timer_obj in timer_list:
        # Проверяем только timer_obj с 6 элементами
        if len(timer_obj) != 6:
            continue

        # Пропускаем timer_obj если status != "active"
        if timer_obj.status != "active":
            continue

        # Проверяем условия и определяем карту
        confirmed_card = check_timer_conditions(timer_obj, card_manager)

        if confirmed_card:
            # Обрабатываем подтвержденный таймер
            process_confirmed_timer(confirmed_card, card_manager, elixir_spent_total, evolution_dict_timer)

            # Помечаем timer_obj как обработанный (НЕ удаляем!)
            timer_obj.status = "done"

    # 5. Удаление timer_obj (ЕДИНСТВЕННОЕ место удаления!)
    # Удаляем ТОЛЬКО когда cnt_box_timer == 0 (таймер исчез с экрана на 1.5+ сек)
    # Независимо от статуса (active, done, bomb, bad, error_1)
    timers_to_remove = []
    for timer_obj in timer_list:
        timer_count = cnt_box_timer(timer_obj)
        if timer_count == 0:
            timers_to_remove.append(timer_obj)

    for timer_obj in timers_to_remove:
        timer_list.remove(timer_obj)

    return elixir_spent_total[0]
