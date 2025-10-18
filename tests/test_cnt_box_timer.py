import sys
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.functions import cnt_box_timer


timer_obj_0 = [[[],[],[],[]],
                                        [[],[],[],[]],
                                        [[],[],[],[]],
                                        [[],[],[],[]]]

# должен вернуть 0, тк нет box_timer
print("0 таймеров:", cnt_box_timer(timer_obj_0))


timer_obj_2 = [[[1,3,4,6],[2],[3],[4]],
                        [[],[],[],[]],
                        [[1,2,3,4],[],[],[1,2,3,4]],
                        [[],[],[],[1,2,3,4]]]

# должен вернуть 2, тк в первой колонке есть 2 box_timer
print("2 таймера: ", cnt_box_timer(timer_obj_2))

timer_obj_6 = [[[1,3,4,6],[2],[3],[4]],
                        [[1,3,4,6],[2],[3],[4]],
                        [[1,3,4,6],[2],[3],[4]],
                        [[1,2,3,4],[],[],[1,2,3,4]],
                        [[1],[],[],[1,2,3,4]],
                        [[1,3],[2],[3],[4]]]

# должен вернуть 6, тк в каждом timer_screen есть по 1 box_timer
print("6 таймеров:", cnt_box_timer(timer_obj_6))
