import sys
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.functions import boxtimer_to_boxzone
from config import get_roi_bounds


box_timer = (100, 100, 120, 110)

roi_x_min, roi_y_min, roi_x_max, roi_y_max = get_roi_bounds()

print(f"roi_x_min: {roi_x_min}, roi_y_min: {roi_y_min}, roi_x_max: {roi_x_max}, roi_y_max: {roi_y_max}")

box_zone = boxtimer_to_boxzone(box_timer)
print(f"box_zone: {box_zone}")