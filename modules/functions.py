from collections import Counter, defaultdict
from typing import List, Tuple
import math



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



def group_box_lvl():
    pass



def boxtimer_to_boxzone():
    pass


