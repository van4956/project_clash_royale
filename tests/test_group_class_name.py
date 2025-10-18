import sys
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.functions import group_class_name


data_1 = [
                            ["а", "а", "а"],
                            ["а", "б"],
                            ["а", "а"],
                            ["б"],
                            ["а", "с"],
                            ["а", "а"],
                        ]

# должен вернуть ['а', 'а'], тк после группировки будет а-5, а-3, б-2, а-1, с-1
print(group_class_name(data_1, threshold=3))

# должен вернуть ['а', 'а', 'б'], тк после группировки будет а-5, а-3, б-2, а-1, с-1
print(group_class_name(data_1, threshold=2))
print('--------------------------------')


data_2 = [
                            ["sceleton","sceleton","rage"],
                            ["sceleton","sceleton","sceleton","rage"],
                            ["sceleton","sceleton"],
                            ["sceleton","sceleton","hunter"],
                            ["sceleton"],
                            ["sceleton","bandit"],
                        ]

# должен вернуть ['WC_sceleton', 'WC_sceleton']
print("t=3: ", group_class_name(data_2, threshold=3))

# должен вернуть ['WC_sceleton', 'WC_sceleton', 'SE_rage']
print("t=2: ", group_class_name(data_2, threshold=2))

# должен вернуть ['WC_sceleton', 'WC_sceleton', 'WC_sceleton', 'WC_hunter', 'SE_rage']
print("t=1: ", group_class_name(data_2, threshold=1))

# должен вернуть ['WC_sceleton', 'WC_sceleton']
print("t=4: ", group_class_name(data_2, threshold=4))

# должен вернуть ['WC_sceleton']
print("t=5: ", group_class_name(data_2, threshold=5))

# должен вернуть ['WC_sceleton']
print("t=6: ", group_class_name(data_2, threshold=6))

# должен вернуть []
print("t=7: ", group_class_name(data_2, threshold=7))
print('--------------------------------')