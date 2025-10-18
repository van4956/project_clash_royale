import sys

class TimerScreen(list):
    def __init__(self, *args, first_screen=None, last_screen=None, list_ignore=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.first_screen = first_screen
        self.last_screen = last_screen
        # избегаем изменяемого значения по умолчанию в аргументе функции
        if list_ignore is None:
            self.list_ignore = []
        else:
            self.list_ignore = list_ignore

x = TimerScreen([1,2,3,4,5], first_screen=1, last_screen=1, list_ignore=None)
x.list_ignore = [1]
x.last_screen=19
print(x, x.first_screen, x.last_screen, x.list_ignore)
print('--------------------------------')

# Добавить элемент в list_ignore
x.list_ignore = x.list_ignore + [2, 3, 4]
x.last_screen=21
print(x, x.first_screen, x.last_screen, x.list_ignore)
print('--------------------------------')

# Удалить все элементы, которые есть в другом списке
to_remove = [1, 3]
x.list_ignore = [item for item in x.list_ignore if item not in to_remove]
x.last_screen=22
print(x, x.first_screen, x.last_screen, x.list_ignore)
print('--------------------------------')

# Можно также удалить конкретное значение так:
item_to_remove = 4
if item_to_remove in x.list_ignore:
    x.list_ignore.remove(item_to_remove)
x.last_screen=23
print(x, x.first_screen, x.last_screen, x.list_ignore)
print('--------------------------------')

# удалить элементы из списка, которые есть в list_ignore
for i in x.list_ignore:
    if i in x:
        x.remove(i)
print(x, x.first_screen, x.last_screen, x.list_ignore)
print('--------------------------------')
