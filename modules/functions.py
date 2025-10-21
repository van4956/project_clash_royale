from collections import Counter, defaultdict
from typing import List, Tuple
import math
from config import get_roi_bounds



Box = Tuple[float, float, float, float]  # (x1, y1, x2, y2)

def iou_box(
    box_a: Box,
    box_b: Box,
    alpha: float = 1,     # значимость IoU в общем скоре (пока что 1, потом скорректирую)
    sigma: float = 0.9    # чувствительность к смещению центров
) -> float:
    """
    Вычисляет композитный скор схожести двух боксов:
      score = alpha * IoU + (1 - alpha) * exp( - (d / (sigma * D))^2 )

    box_a, box_b: (x1, y1, x2, y2) с произвольным порядком (нормализуем внутри)
    alpha:   чем больше вес IoU, тем меньше роль расстояния центров.
    sigma:   при высоком sigma расстояние слабее наказывает, при низком sigma — значимость расстояния центров строже.

    Возвращает число в [0, 1]. Чем выше — тем «похожее».
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



def group_class_name(rows: List[List[str]], threshold: int = 3) -> List[str]:
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
    - Вниз от верхней границы на 2 высоты бокса таймера
    - Нижняя граница остается на месте
    - Ограничение границами ROI (не выходим за пределы области детекции)

    Args:
        box_timer: (x1, y1, x2, y2) координаты бокса таймера

    Returns:
        box_zone: (x1, y1, x2, y2) расширенная зона отслеживания (ограниченная ROI)

    Пример:
        box_timer = (100, 100, 120, 110)  # ширина=20, высота=10
        box_zone = (60, 120, 160, 110)    # x1-40, y1+20, x2+40, y2 (если в пределах ROI)

    Обоснование ограничения ROI:
        Если таймер находится у края ROI, расширенная зона может выйти за границы.
        Модель детекции работает только внутри ROI, поэтому за пределами детекций нет.
        Ограничение box_zone границами ROI обеспечивает корректность поиска box_lvl и class_name.
    """
    x1, y1, x2, y2 = box_timer

    # Нормализация координат (на случай если x1>x2 или y1>y2)
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)

    # Вычисляем размеры бокса таймера
    width = x2 - x1   # ширина (l)
    height = y2 - y1  # высота (h)

    # Создаем расширенную зону
    zone_x1 = x1 - 2 * width   # влево на 2 ширины
    zone_y1 = y1 + 2 * height  # вниз от верхней границы на 2 высоты
    zone_x2 = x2 + 2 * width   # вправо на 2 ширины
    zone_y2 = y2               # нижняя граница остается

    # Получаем границы ROI из конфигурации
    roi_x_min, roi_y_min, roi_x_max, roi_y_max = get_roi_bounds()

    # Ограничиваем box_zone границами ROI
    # Это критично! Если таймер у края ROI, расширенная зона может выйти за пределы.
    # Детекции модели существуют только внутри ROI, поэтому поиск за пределами бессмыслен.
    zone_x1 = max(roi_x_min, zone_x1)  # слева: не выходим за левую границу ROI
    zone_y1 = max(roi_y_min, zone_y1)  # сверху: не выходим за верхнюю границу ROI
    zone_x2 = min(roi_x_max, zone_x2)  # справа: не выходим за правую границу ROI
    zone_y2 = min(roi_y_max, zone_y2)  # снизу: не выходим за нижнюю границу ROI

    return (zone_x1, zone_y1, zone_x2, zone_y2)



def group_box_lvl(timer_obj: List[List], threshold: int = 3, iou_threshold: float = 0.7) -> int:
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
