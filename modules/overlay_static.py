# -*- coding: utf-8 -*-
"""
Модуль для статичных overlay элементов
Элементы создаются при запуске и остаются неизменными

Платформа: Windows 11 only
"""

import tkinter as tk
from PIL import Image, ImageTk
import ctypes  # Windows API для click-through окна
import os

class StaticOverlay:
    """
    Класс для создания статичных overlay элементов

    Создаем два отдельных окна:
    - Окно 1: Полупрозрачная красная доска (фон)
    - Окно 2: Капелька эликсира поверх доски
    """

    def __init__(self, drop_image_path, drop_x, drop_y, drop_width,
                 board_x, board_y, board_width, board_height, board_alpha, board_color):
        """
        Инициализация статичного overlay

        Args:
            drop_image_path (str): Путь к изображению капельки
            drop_x (int): X координата капельки (абсолютная)
            drop_y (int): Y координата капельки (абсолютная)
            drop_width (int): Целевая ширина капельки
            board_x (int): X координата доски (абсолютная)
            board_y (int): Y координата доски (абсолютная)
            board_width (int): Ширина доски
            board_height (int): Высота доски
            board_alpha (float): Прозрачность доски
            board_color (tuple): Цвет доски (RGB)
        """
        self.drop_image_path = drop_image_path  # путь к PNG файлу капельки
        self.drop_x = drop_x  # где рисовать капельку по X
        self.drop_y = drop_y  # где рисовать капельку по Y
        self.drop_width = drop_width  # желаемая ширина капельки

        self.board_x = board_x  # где рисовать доску по X
        self.board_y = board_y  # где рисовать доску по Y
        self.board_width = board_width  # ширина доски
        self.board_height = board_height  # высота доски

        # Окно для доски
        self.board_root = None  # Tkinter окно для доски
        self.board_canvas = None  # Canvas для рисования доски

        # Окно для капельки
        self.drop_root = None  # Tkinter окно для капельки
        self.drop_canvas = None  # Canvas для отображения капельки
        self.drop_photo = None  # PhotoImage объект (нужен для отображения)

        self.drop_real_width = 0  # реальная ширина капельки после масштабирования
        self.drop_real_height = 0  # реальная высота капельки после масштабирования

        # Цвета
        self.COLOR_BACKGROUND = '#FFFFFF'   # цвет для фона который потом станет прозрачным
        self.COLOR_BOARD = board_color  # цвет доски
        self.BOARD_ALPHA = board_alpha  # прозрачность доски

    def create_windows(self):
        """
        Создание двух отдельных окон: доска и капелька

        Returns:
            bool: True если успешно создано
        """
        # Проверяем что файл с капелькой существует
        if not os.path.exists(self.drop_image_path):
            print(f"ОШИБКА: Изображение капельки не найдено: {self.drop_image_path}")
            return False

        try:
            # ========================================
            # ЧАСТЬ 1: СОЗДАЕМ ОКНО ДЛЯ ДОСКИ
            # ========================================

            self.board_root = tk.Tk()  # создаем новое окно
            self.board_root.title("Board")  # заголовок окна (не видно, т.к. безрамочное)
            self.board_root.overrideredirect(True)  # убираем рамку окна и кнопки (min/max/close)
            self.board_root.attributes('-topmost', True)  # окно поверх всех остальных
            self.board_root.attributes('-transparentcolor', self.COLOR_BACKGROUND)  # делаем цвет для фона прозрачным
            self.board_root.attributes('-alpha', self.BOARD_ALPHA)  # устанавливаем прозрачность окна

            # Устанавливаем размер и позицию окна: ширина x высота + X + Y
            self.board_root.geometry(f'{self.board_width}x{self.board_height}+{self.board_x}+{self.board_y}')

            # Создаем холст (canvas) для рисования
            self.board_canvas = tk.Canvas(
                self.board_root,  # родительское окно
                width=self.board_width,  # ширина холста
                height=self.board_height,  # высота холста
                bg=self.COLOR_BACKGROUND,  # фон холста (далее станет прозрачным)
                highlightthickness=0  # убираем рамку вокруг холста
            )
            self.board_canvas.pack()  # размещаем холст в окне

            # Конвертируем RGB кортеж в HEX строку для tkinter
            board_color_hex = f'#{self.COLOR_BOARD[0]:02x}{self.COLOR_BOARD[1]:02x}{self.COLOR_BOARD[2]:02x}'

            self.board_canvas.create_rectangle(
                0, 0,  # левый верхний угол
                self.board_width, self.board_height,  # правый нижний угол
                fill=board_color_hex,  # цвет заливки в HEX формате
                outline=''  # без обводки
            )

            self.board_root.update_idletasks()  # обновляем окно чтобы получить его ID

            # === WINDOWS API: делаем окно некликабельным (click-through) ===
            hwnd = ctypes.windll.user32.GetParent(self.board_root.winfo_id())  # получаем дескриптор окна (ID в Windows)

            GWL_EXSTYLE = -20  # индекс расширенного стиля окна
            WS_EX_LAYERED = 0x00080000  # флаг: окно поддерживает прозрачность
            WS_EX_TRANSPARENT = 0x00000020  # флаг: окно пропускает клики мыши

            current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)  # получаем текущий стиль окна
            new_style = current_style | WS_EX_LAYERED | WS_EX_TRANSPARENT  # добавляем нужные флаги
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)  # применяем новый стиль

            print("Окно доски создано")

            # ========================================
            # ЧАСТЬ 2: СОЗДАЕМ ОКНО ДЛЯ КАПЕЛЬКИ
            # ========================================

            # Загружаем изображение капельки
            drop_img = Image.open(self.drop_image_path)  # открываем PNG файл
            drop_img = drop_img.convert('RGBA')  # конвертируем в формат RGBA (Red, Green, Blue, Alpha)
            original_width, original_height = drop_img.size  # получаем оригинальные размеры

            # Вычисляем новый размер с сохранением пропорций (aspect ratio)
            aspect_ratio = original_height / original_width  # соотношение высоты к ширине
            self.drop_real_width = int(self.drop_width)  # новая ширина (заданная)
            self.drop_real_height = int(self.drop_real_width * aspect_ratio)  # новая высота (пропорциональная)

            # Масштабируем изображение
            drop_img = drop_img.resize(
                (self.drop_real_width, self.drop_real_height),  # новый размер
                Image.Resampling.LANCZOS  # алгоритм масштабирования (высокое качество)
            )

            # Создаем окно для капельки (дочернее от board_root)
            self.drop_root = tk.Toplevel(self.board_root)  # создаем дочернее окно (не второе корневое!)
            self.drop_root.title("Drop")  # заголовок окна
            self.drop_root.overrideredirect(True)  # убираем рамку окна
            self.drop_root.attributes('-topmost', True)  # окно поверх всех
            self.drop_root.attributes('-transparentcolor', self.COLOR_BACKGROUND)  # этот цвет станет прозрачным
            # self.drop_root.attributes('-transparentcolor', "#FFFFFF")

            # Устанавливаем размер и позицию окна
            self.drop_root.geometry(f'{self.drop_real_width}x{self.drop_real_height}+{self.drop_x}+{self.drop_y}')

            # Создаем холст для отображения капельки
            self.drop_canvas = tk.Canvas(
                self.drop_root,  # родительское окно
                width=self.drop_real_width,  # ширина
                height=self.drop_real_height,  # высота
                bg=self.COLOR_BACKGROUND,  # фон (станет прозрачным)
                highlightthickness=0  # без рамки
            )

            self.drop_canvas.pack()  # размещаем холст

            # Конвертируем PIL изображение в Tkinter PhotoImage
            self.drop_photo = ImageTk.PhotoImage(drop_img)  # нужно сохранить в self, иначе garbage collector удалит

            # Размещаем изображение на холсте
            self.drop_canvas.create_image(
                0, 0,  # позиция на холсте
                anchor=tk.NW,  # привязка к левому верхнему углу (North-West)
                image=self.drop_photo  # изображение для отображения
            )

            self.drop_root.update_idletasks()  # обновляем окно

            # === WINDOWS API: делаем окно капельки некликабельным ===
            hwnd_drop = ctypes.windll.user32.GetParent(self.drop_root.winfo_id())  # получаем дескриптор окна

            current_style = ctypes.windll.user32.GetWindowLongW(hwnd_drop, GWL_EXSTYLE)  # текущий стиль
            new_style = current_style | WS_EX_LAYERED | WS_EX_TRANSPARENT  # добавляем флаги
            ctypes.windll.user32.SetWindowLongW(hwnd_drop, GWL_EXSTYLE, new_style)  # применяем


            print("Окно капельки создано")

            # Финальное обновление обоих окон
            self.board_root.update()
            self.drop_root.update()

            return True

        except Exception as e:
            print(f"ОШИБКА при создании статичного overlay: {e}")
            import traceback
            traceback.print_exc()
            return False

    @property
    def width(self):
        """Возвращает ширину капельки (для обратной совместимости)"""
        return self.drop_real_width

    @property
    def height(self):
        """Возвращает высоту капельки (для обратной совместимости)"""
        return self.drop_real_height

    def update(self):
        """Обновление обоих окон (доска + капелька)"""
        # Обновляем окно доски
        if self.board_root:
            try:
                self.board_root.update()  # обновляем окно чтобы оно оставалось отзывчивым
            except tk.TclError:  # если окно было закрыто
                pass

        # Обновляем окно капельки
        if self.drop_root:
            try:
                self.drop_root.update()  # обновляем окно чтобы оно оставалось отзывчивым
            except tk.TclError:  # если окно было закрыто
                pass

    def close(self):
        """Закрытие обоих окон"""
        # Закрываем окно капельки
        if self.drop_root:
            try:
                self.drop_root.destroy()  # уничтожаем окно и освобождаем ресурсы
                print("✓ Окно капельки закрыто")
            except Exception as e:
                print(f"Предупреждение при закрытии капельки: {e}")
            finally:
                self.drop_root = None  # обнуляем ссылку
                self.drop_canvas = None  # обнуляем ссылку
                self.drop_photo = None  # обнуляем ссылку (освобождаем память)

        # Закрываем окно доски
        if self.board_root:
            try:
                self.board_root.destroy()  # уничтожаем окно и освобождаем ресурсы
                print("✓ Окно доски закрыто")
            except Exception as e:
                print(f"Предупреждение при закрытии доски: {e}")
            finally:
                self.board_root = None  # обнуляем ссылку
                self.board_canvas = None  # обнуляем ссылку

        print("Статичный overlay закрыт.")
