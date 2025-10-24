# -*- coding: utf-8 -*-
"""
Модуль захвата экрана
Отвечает за выбор области экрана пользователем и последующий захват кадров
"""

import logging
import os  # Для работы с файловой системой

# Настраиваем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)

import cv2  # OpenCV - библиотека компьютерного зрения
import numpy as np  # NumPy - для работы с массивами и изображениями
import mss  # MSS - быстрая библиотека для захвата экрана (быстрее чем PIL)
from config import (
    ROI_CONFIG_PATH,  # Путь к файлу с сохраненными координатами
    SELECTION_COLOR,  # Цвет рамки выделения
    SELECTION_THICKNESS,  # Толщина линии рамки
)


class ScreenCapture:
    """
    Класс для захвата экрана

    Функционал:
    1. Выбор области экрана пользователем (ROI - Region of Interest)
    2. Сохранение координат области в файл
    3. Загрузка координат из файла при повторном запуске
    4. Захват кадров из выбранной области
    """

    def __init__(self):
        """
        Инициализация класса захвата экрана
        """
        # Координаты выбранной области (None до выбора области)
        self.roi = None  # ROI будет словарем: {"top": y, "left": x, "width": w, "height": h}

        # Объект MSS для захвата экрана (инициализируется при первом использовании)
        self.sct = mss.mss()

        # Временные переменные для выбора области мышью
        self.start_point = None  # Начальная точка выделения (x, y)
        self.end_point = None  # Конечная точка выделения (x, y)
        self.selecting = False  # Флаг процесса выделения

    def mouse_callback(self, event, x, y, flags, param):
        """
        Callback функция для обработки событий мыши при выборе области

        Args:
            event: Тип события мыши (нажатие, отпускание, движение)
            x: X координата курсора
            y: Y координата курсора
            flags: Дополнительные флаги (не используются)
            param: Дополнительные параметры (не используются)
        """
        # Нажатие левой кнопки мыши - начало выделения области
        if event == cv2.EVENT_LBUTTONDOWN:
            self.start_point = (x, y)
            self.end_point = (x, y)
            self.selecting = True

        # Движение мыши с зажатой кнопкой - обновление конечной точки
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.selecting:
                self.end_point = (x, y)

        # Отпускание левой кнопки мыши - завершение выделения
        elif event == cv2.EVENT_LBUTTONUP:
            self.end_point = (x, y)
            self.selecting = False

    def select_roi(self):
        """
        Интерактивный выбор области экрана пользователем

        Пользователь видит полный скриншот экрана и выделяет нужную область мышью.
        После нажатия Enter координаты сохраняются.

        Returns:
            dict: Словарь с координатами области {"top": y, "left": x, "width": w, "height": h}
                  или None если пользователь отменил выбор (ESC)
        """
        # Делаем полный скриншот экрана для выбора области
        with mss.mss() as sct:
            # Захватываем первый монитор (при нескольких мониторах можно выбрать другой)
            monitor = sct.monitors[1]  # monitors[0] - все мониторы, monitors[1] - первый монитор
            screenshot = sct.grab(monitor)

            # Конвертируем скриншот в формат numpy array для OpenCV
            img = np.array(screenshot)
            # MSS возвращает изображение в формате BGRA, конвертируем в BGR для OpenCV
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Создаем копию изображения для рисования рамки выделения
        # img_copy = img.copy()

        # Создаем окно для отображения скриншота
        window_name = "Select ROI"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)  # Устанавливаем удобный размер окна

        # Привязываем callback функцию для обработки событий мыши
        cv2.setMouseCallback(window_name, self.mouse_callback)

        # Выводим инструкцию для пользователя
        logger.info("Выделите область игры мышью и нажмите Enter. ESC для отмены.")

        # Основной цикл выбора области
        while True:
            # Создаем новую копию изображения для отрисовки текущей рамки
            img_display = img.copy()

            # Если пользователь выделяет область, рисуем прямоугольник
            if self.start_point and self.end_point:
                cv2.rectangle(
                    img_display,
                    self.start_point,
                    self.end_point,
                    SELECTION_COLOR,
                    SELECTION_THICKNESS
                )

            # Отображаем изображение с рамкой
            cv2.imshow(window_name, img_display)

            # Ожидаем нажатия клавиши (1 мс задержка для обновления окна)
            key = cv2.waitKey(1) & 0xFF

            # Enter (13) - подтверждение выбора
            if key == 13:  # Enter key
                if self.start_point and self.end_point:
                    # Вычисляем координаты области (обрабатываем случай, когда тянули справа налево)
                    x1 = min(self.start_point[0], self.end_point[0])
                    y1 = min(self.start_point[1], self.end_point[1])
                    x2 = max(self.start_point[0], self.end_point[0])
                    y2 = max(self.start_point[1], self.end_point[1])

                    # Формируем словарь с координатами в формате MSS
                    self.roi = {
                        "top": y1,      # Верхняя координата
                        "left": x1,     # Левая координата
                        "width": x2 - x1,   # Ширина области
                        "height": y2 - y1   # Высота области
                    }

                    # Сохраняем координаты в файл для последующих запусков
                    self.save_roi()
                    break

            # ESC (27) - отмена выбора
            elif key == 27:  # ESC key
                logger.info("Выбор области отменен")
                cv2.destroyAllWindows()
                return None

        # Закрываем окно выбора
        cv2.destroyAllWindows()

        return self.roi

    def save_roi(self):
        """
        Сохранение координат выбранной области в текстовый файл

        Формат файла: top,left,width,height
        Пример: 100,200,800,600
        """
        if self.roi:
            # Записываем координаты в файл в формате CSV (разделитель - запятая)
            with open(ROI_CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(f"{self.roi['top']},{self.roi['left']},{self.roi['width']},{self.roi['height']}")


    def load_roi(self):
        """
        Загрузка координат области из файла (если он существует)

        Returns:
            bool: True если координаты успешно загружены, False если файл не найден
        """
        # Проверяем существование файла с координатами
        if os.path.exists(ROI_CONFIG_PATH):
            # Читаем координаты из файла
            with open(ROI_CONFIG_PATH, 'r', encoding='utf-8') as f:
                coords = f.read().strip().split(',')

                # Парсим координаты и создаем словарь ROI
                self.roi = {
                    "top": int(coords[0]),      # Верхний отступ
                    "left": int(coords[1]),     # Левый отступ
                    "width": int(coords[2]),    # Ширина
                    "height": int(coords[3])    # Высота
                }

            logger.info("Координаты области загружены из файла")
            return True

        return False

    def capture_frame(self):
        """
        Захват одного кадра из выбранной области экрана

        Returns:
            numpy.ndarray: Изображение в формате BGR (OpenCV формат) или None если ROI не установлен
        """
        # Проверяем, что область выбрана
        if self.roi is None:
            logger.error("ОШИБКА: ROI не установлен. Сначала выберите область.")
            return None

        # Захватываем кадр из выбранной области
        screenshot = self.sct.grab(self.roi)

        # Конвертируем в numpy array
        frame = np.array(screenshot)

        # Конвертируем из BGRA в BGR (убираем альфа-канал)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        return frame

    def cleanup(self):
        """
        Очистка ресурсов (закрытие MSS объекта)
        Вызывается при завершении работы программы
        """
        if self.sct:
            self.sct.close()
