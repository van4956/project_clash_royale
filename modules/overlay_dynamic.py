# -*- coding: utf-8 -*-
"""
Модуль для динамических overlay элементов
Элементы обновляются каждый кадр (шкала эликсира, цифры, карты)
"""

import os
import logging

# Настраиваем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)

import tkinter as tk
import ctypes  # Windows API для click-through окна
from PIL import Image, ImageTk
from config import CARD_SCALE


class DynamicOverlay:
    """
    Класс для создания динамических overlay элементов

    Элементы:
    - Цифра текущего эликсира поверх капельки (0-10)
    - Горизонтальная шкала эликсира
    - Карты ожидания (слева, ниже шкалы)
    - Карты в руке (справа, ниже шкалы)
    """

    def __init__(self, x, y, width, height, drop_x, drop_y, drop_width, drop_height, board_y, board_height):
        """
        Инициализация динамического overlay

        Args:
            x (int): X координата шкалы, равна X координата центра капельки + ширина капельки + отступ от капельки в % от высоты капельки
            y (int): Y координата шкалы, равна Y координата центра капельки
            width (int): Ширина шкалы равна в % от ширины ROI
            height (int): Высота шкалы равна в % от высоты капельки
            drop_x (int): X координата центра капельки (для цифры)
            drop_y (int): Y координата центра капельки (для цифры)
            drop_width (int): Ширина капельки
            drop_height (int): Высота капельки
            board_y (int): Y координата доски (для расчета позиций карт)
            board_height (int): Высота доски (для расчета позиций карт)
        """
        # Параметры шкалы
        self.bar_x = x
        self.bar_y = y
        self.width = width
        self.height = height

        # Параметры капельки
        self.drop_x = drop_x
        self.drop_y = drop_y
        self.drop_width = drop_width
        self.drop_height = drop_height

        # Параметры доски (для расчета позиций карт)
        self.board_y = board_y
        self.board_height = board_height

        self.root = None
        self.canvas = None
        self.current_elixir = 0  # Текущее количество эликсира

        # Координаты для карт (рассчитываются позже)
        self.await_card_positions = []  # [(x, y), (x, y), (x, y), (x, y)]
        self.hand_card_positions = []   # [(x, y), (x, y), (x, y), (x, y)]

        # Хранение изображений карт (для отображения)
        self.await_card_images = []  # [PhotoImage, ...] - для карт ожидания
        self.hand_card_images = []   # [PhotoImage, ...] - для карт в руке
        self.await_card_ids = []     # [canvas_id, ...] - ID объектов на canvas для await
        self.hand_card_ids = []      # [canvas_id, ...] - ID объектов на canvas для hand

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
            total_width = (self.bar_x + self.width) - self.drop_x + 50
            total_height = max(self.drop_height, self.height + (self.bar_y - self.drop_y)) + 100

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

            logger.info("Динамический overlay создан")

            # Отрисовываем начальное состояние
            self.update_display(0)

            self.root.update()
            return True

        except Exception as e:
            logger.error("ОШИБКА при создании динамического overlay: %s", e)
            return False

    def update_display(self, elixir_amount):
        """
        Обновление отображения шкалы и цифры

        Args:
            elixir_amount (float): Текущее количество эликсира (0-10)
        """
        if not self.canvas:
            logger.warning("Canvas не найден! Пропускаем обновление шкалы и цифры ...")
            return


        self.current_elixir = elixir_amount

        # Очищаем только элементы шкалы и цифры (НЕ трогаем карты!)
        self.canvas.delete("elixir_bar")
        self.canvas.delete("elixir_digit")

        # Вычисляем локальные координаты (относительно окна)
        bar_x = self.bar_x - self.drop_x
        bar_y = self.bar_y - self.drop_y

        # === ОТРИСОВКА ШКАЛЫ ===

        # 1. Фон шкалы (пустая)
        self.canvas.create_rectangle(
            bar_x, bar_y,
            bar_x + self.width, bar_y + self.height,
            outline=self.COLOR_BORDER,
            width=2,
            fill='',
            tags="elixir_bar"
        )

        # 2. Заливка эликсира
        if elixir_amount > 0:
            fill_width = (self.width / 10) * elixir_amount
            self.canvas.create_rectangle(
                bar_x, bar_y,
                bar_x + fill_width, bar_y + self.height,
                fill=self.COLOR_FILL,
                outline='',
                tags="elixir_bar"
            )

        # 3. Деления на 10 частей (вертикальные линии)
        section_width = self.width / 10
        for i in range(1, 10):  # 9 линий (между 10 секциями)
            line_x = bar_x + (section_width * i)
            self.canvas.create_line(
                line_x, bar_y,
                line_x, bar_y + self.height,
                fill=self.COLOR_BORDER,
                width=3,
                tags="elixir_bar"
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
            font=('Arial', font_size, 'bold'),
            tags="elixir_digit"
        )

    def update(self):
        """Обновление окна"""
        if self.root:
            try:
                self.root.update()
            except tk.TclError as e:
                logger.error("Ошибка при обновлении окна: %s", e)


    def _calculate_card_positions(self):
        """
        Расчет координат для размещения карт.

        Алгоритм:
        1. Находим левый нижний угол шкалы (bar_x, bar_y + bar_height)
        2. Находим правый нижний угол шкалы (bar_x + bar_width, bar_y + bar_height)
        3. Опускаем перпендикуляры до нижнего края доски
        4. Находим центры перпендикуляров (C1 и C2)
        5. Проводим отрезок C1-C2 (параллельно шкале, между шкалой и краем доски)
        6. Делим отрезок на 8 равных частей (9 точек)
        7. Точки 0-3: await_cards, точка 4: пропуск, точки 5-8: hand_cards

        Returns:
            tuple: (await_positions, hand_positions)
                   await_positions: [(x, y), ...] - 4 координаты для карт ожидания
                   hand_positions: [(x, y), ...] - 4 координаты для карт в руке
        """
        # Шкала (в абсолютных координатах экрана)
        bar_x = self.bar_x
        bar_y = self.bar_y
        bar_width = self.width
        bar_height = self.height

        # Доска (в абсолютных координатах экрана)
        board_bottom = self.board_y + self.board_height

        # Левый нижний угол шкалы
        left_bottom_x = bar_x
        left_bottom_y = bar_y + bar_height

        # Правый нижний угол шкалы
        right_bottom_x = bar_x + bar_width
        right_bottom_y = bar_y + bar_height

        # Центры перпендикуляров (C1 и C2)
        # C1: центр левого перпендикуляра
        c1_x = left_bottom_x
        c1_y = (left_bottom_y + board_bottom) / 2

        # C2: центр правого перпендикуляра
        c2_x = right_bottom_x
        c2_y = (right_bottom_y + board_bottom) / 2

        # Делим отрезок C1-C2 на 8 равных частей (9 точек)
        step = bar_width / 8

        all_positions = []
        for i in range(9):
            x = c1_x + step * i
            y = c1_y  # Все точки на одной высоте
            all_positions.append((x, y))

        # Распределяем точки:
        # await_cards: точки 0, 1, 2, 3
        # пропуск: точка 4
        # hand_cards: точки 5, 6, 7, 8
        await_positions = [all_positions[i] for i in range(4)]
        hand_positions = [all_positions[i] for i in range(5, 9)]

        return await_positions, hand_positions

    def _load_and_scale_card_image(self, card):
        """
        Загрузка и масштабирование изображения карты.

        Args:
            card: объект Card с атрибутом image_path

        Returns:
            ImageTk.PhotoImage: готовое изображение для отображения на canvas
        """
        try:
            # Определяем путь к изображению
            # Если карта эволюционная и cnt_evo >= target_evo, используем эво версию
            if card.evolution and card.cnt_evo >= card.target_evo and card.evolution_image_path:
                image_path = card.evolution_image_path
            else:
                image_path = card.image_path

            # Проверяем существование файла
            if not os.path.exists(image_path):
                # Если файл не найден, возвращаем None
                logger.error("Файл изображения карты %s не найден: %s", card.card_name, image_path)
                return None

            # Загружаем изображение
            img = Image.open(image_path)
            img = img.convert('RGBA')

            # Масштабируем по CARD_SCALE
            original_width, original_height = img.size
            new_width = int(original_width * CARD_SCALE)
            new_height = int(original_height * CARD_SCALE)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Конвертируем в PhotoImage для tkinter
            photo = ImageTk.PhotoImage(img, master=self.root)  # master=self.root для привязки к правильному окну

            return photo

        except Exception as e:
            logger.error("Ошибка загрузки изображения карты %s: %s", card.card_name, e)
            return None

    def set_await_cards(self, cards_list):
        """
        Установить карты ожидания (слева).

        Args:
            cards_list: список из 4 объектов Card
        """
        if not self.canvas:
            logger.warning("Canvas не найден! Пропускаем установку карт ожидания ...")
            return

        # Рассчитываем координаты если еще не рассчитаны
        if not self.await_card_positions:
            await_pos, hand_pos = self._calculate_card_positions()
            self.await_card_positions = await_pos
            self.hand_card_positions = hand_pos
            logger.info("Координаты карт заново рассчитаны")

        # Удаляем старые изображения с canvas
        for card_id in self.await_card_ids:
            try:
                self.canvas.delete(card_id)
            except Exception as e:
                logger.error("Ошибка удаления изображения карты %s: %s", card_id, e)

        self.await_card_ids.clear()
        self.await_card_images.clear()

        # Отрисовываем новые карты
        for i, card in enumerate(cards_list):
            if i >= 4:  # Только 4 карты
                break

            try:
                # Загружаем и масштабируем изображение
                photo = self._load_and_scale_card_image(card)

                if photo:
                    # Сохраняем ссылку на изображение (иначе garbage collector удалит)
                    self.await_card_images.append(photo)

                    # Получаем координаты (абсолютные на экране)
                    abs_x, abs_y = self.await_card_positions[i]

                    # Конвертируем в координаты относительно canvas
                    # Canvas начинается с drop_x, drop_y
                    rel_x = abs_x - self.drop_x
                    rel_y = abs_y - self.drop_y

                    # Отрисовываем на canvas (anchor='center' - центрируем по координатам)
                    card_id = self.canvas.create_image(
                        rel_x, rel_y,
                        image=photo,
                        anchor='center'
                    )

                    self.await_card_ids.append(card_id)

            except Exception as e:
                logger.error("Ошибка отрисовки await карты %s (%s): %s", i, card.card_name, e)

    def set_hand_cards(self, cards_list):
        """
        Установить карты в руке (справа).

        Args:
            cards_list: список из 4 объектов Card
        """
        if not self.canvas:
            logger.error("Canvas не найден! Пропускаем установку карт в руке ...")
            return

        # Рассчитываем координаты если еще не рассчитаны
        if not self.await_card_positions:
            await_pos, hand_pos = self._calculate_card_positions()
            self.await_card_positions = await_pos
            self.hand_card_positions = hand_pos

        # Удаляем старые изображения с canvas
        for card_id in self.hand_card_ids:
            try:
                self.canvas.delete(card_id)
            except Exception as e:
                logger.error("Ошибка удаления изображения карты %s: %s", card_id, e)

        self.hand_card_ids.clear()
        self.hand_card_images.clear()

        # Отрисовываем новые карты
        for i, card in enumerate(cards_list):
            if i >= 4:  # Только 4 карты
                break

            try:
                # Загружаем и масштабируем изображение
                photo = self._load_and_scale_card_image(card)

                if photo:
                    # Сохраняем ссылку на изображение
                    self.hand_card_images.append(photo)

                    # Получаем координаты (абсолютные на экране)
                    abs_x, abs_y = self.hand_card_positions[i]

                    # Конвертируем в координаты относительно canvas
                    rel_x = abs_x - self.drop_x
                    rel_y = abs_y - self.drop_y

                    # Отрисовываем на canvas
                    card_id = self.canvas.create_image(
                        rel_x, rel_y,
                        image=photo,
                        anchor='center'
                    )

                    self.hand_card_ids.append(card_id)
                    # logger.info("Орисовка hand карты %s (%s) на canvas", i, card.card_name)

            except Exception as e:
                logger.error("Ошибка отрисовки hand карты %s (%s): %s", i, card.card_name, e)

    def close(self):
        """Закрытие окна"""
        if self.root:
            try:
                self.root.destroy()
                logger.info("Динамический overlay закрыт.")
            except Exception as e:
                logger.warning("Предупреждение при закрытии: %s", e)
            finally:
                self.root = None
                self.canvas = None
