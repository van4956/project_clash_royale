# -*- coding: utf-8 -*-
"""
Модуль для динамических overlay элементов
Элементы обновляются каждый кадр (шкала эликсира, цифры)
"""

import tkinter as tk
import ctypes  # Windows API для click-through окна


class DynamicOverlay:
    """
    Класс для создания динамических overlay элементов

    Элементы:
    - Горизонтальная шкала эликсира (0-10)
    - Цифра текущего эликсира поверх капельки
    """

    def __init__(self, x, y, width, height, drop_x, drop_y, drop_width, drop_height):
        """
        Инициализация динамического overlay

        Args:
            x (int): X координата шкалы
            y (int): Y координата шкалы
            width (int): Ширина шкалы
            height (int): Высота шкалы
            drop_x (int): X координата капельки (для цифры)
            drop_y (int): Y координата капельки (для цифры)
            drop_width (int): Ширина капельки
            drop_height (int): Высота капельки
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.drop_x = drop_x
        self.drop_y = drop_y
        self.drop_width = drop_width
        self.drop_height = drop_height

        self.root = None
        self.canvas = None
        self.current_elixir = 0  # Текущее количество эликсира

        # Цвета
        self.COLOR_BACKGROUND = '#FFFFFF'   # Цвет для фона который потом станет прозрачным (FFFFFF - белый, 000000 - черный)
        self.COLOR_BORDER = '#404040'       # Темно-серый
        self.COLOR_FILL = '#FF4FC3'         # Розовый
        self.COLOR_TEXT = '#404040'         # Темно-серый

    def create_window(self):
        """
        Создание окна с динамическими элементами

        Returns:
            bool: True если успешно создано
        """
        try:
            # Создаем окно для шкалы и цифры
            # Нужно охватить область от капельки до конца шкалы
            total_width = (self.x + self.width) - self.drop_x
            total_height = max(self.drop_height, self.height + (self.y - self.drop_y))

            self.root = tk.Tk()
            self.root.title("Clash Royale Bot - Dynamic")
            self.root.overrideredirect(True)  # Убираем рамку и заголовок окна (безрамочный режим)
            self.root.attributes('-topmost', True)  # Окно поверх всех остальных окон
            self.root.attributes('-transparentcolor', self.COLOR_BACKGROUND)  # Делаем указанный фон прозрачным

            # Позиционируем окно СРАЗУ после создания
            self.root.geometry(f'{total_width}x{total_height}+{self.drop_x}+{self.drop_y}')

            # Обновляем окно перед получением hwnd
            self.root.update_idletasks()

            # Делаем окно некликабельным через Windows API
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020

            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

            # Canvas
            self.canvas = tk.Canvas(
                self.root,
                width=total_width,
                height=total_height,
                bg=self.COLOR_BACKGROUND,
                highlightthickness=0
            )
            self.canvas.pack()

            print("Динамический overlay создан")

            # Отрисовываем начальное состояние
            self.update_display(0)

            self.root.update()
            return True

        except Exception as e:
            print(f"ОШИБКА при создании динамического overlay: {e}")
            return False

    def update_display(self, elixir_amount):
        """
        Обновление отображения шкалы и цифры

        Args:
            elixir_amount (float): Текущее количество эликсира (0-10)
        """
        if not self.canvas:
            return

        # Ограничиваем 0-10
        elixir_amount = max(0, min(10, elixir_amount))
        self.current_elixir = elixir_amount

        # Очищаем canvas
        self.canvas.delete("all")

        # Вычисляем локальные координаты (относительно окна)
        bar_x = self.x - self.drop_x
        bar_y = self.y - self.drop_y

        # === ОТРИСОВКА ШКАЛЫ ===

        # 1. Фон шкалы (пустая)
        self.canvas.create_rectangle(
            bar_x, bar_y,
            bar_x + self.width, bar_y + self.height,
            outline=self.COLOR_BORDER,
            width=2,
            fill=''
        )

        # 2. Заливка эликсира
        if elixir_amount > 0:
            fill_width = (self.width / 10) * elixir_amount
            self.canvas.create_rectangle(
                bar_x, bar_y,
                bar_x + fill_width, bar_y + self.height,
                fill=self.COLOR_FILL,
                outline=''
            )

        # 3. Деления на 10 частей (вертикальные линии)
        section_width = self.width / 10
        for i in range(1, 10):  # 9 линий (между 10 секциями)
            line_x = bar_x + (section_width * i)
            self.canvas.create_line(
                line_x, bar_y,
                line_x, bar_y + self.height,
                fill=self.COLOR_BORDER,
                width=3
            )

        # === ОТРИСОВКА ЦИФРЫ НА КАПЕЛЬКЕ ===

        # Вычисляем размер шрифта относительно размера капельки
        font_size = int(self.drop_height * 0.25)  # % от высоты капельки

        # Центр капельки (локальные координаты)
        text_x = self.drop_width // 2
        text_y = self.drop_height // 2

        # Отрисовываем цифру
        self.canvas.create_text(
            text_x, text_y,
            text=str(int(elixir_amount)),
            fill=self.COLOR_TEXT,
            font=('Arial', font_size, 'bold')
        )

    def update(self):
        """Обновление окна"""
        if self.root:
            try:
                self.root.update()
            except tk.TclError:
                pass

    def close(self):
        """Закрытие окна"""
        if self.root:
            try:
                self.root.destroy()
                print("Динамический overlay закрыт.")
            except Exception as e:
                print(f"Предупреждение при закрытии: {e}")
            finally:
                self.root = None
                self.canvas = None
