from collections import Counter, defaultdict
from typing import List, Tuple




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






def cnt_box_timer(timer_obj: List[List[List[int]]]) -> int:
    '''
    Подсчитывает количество box_timer (первый элемент timer_screen) в timer_obj.
    Принимает объект timer_obj, состоящий из 6 timer_screen.
    Возвращает число,количество box_timer.
    '''
    x = sum(1 for timer_screen in timer_obj if timer_screen[0])

    return x
