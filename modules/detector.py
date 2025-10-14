# -*- coding: utf-8 -*-
"""
Модуль детекции объектов с помощью YOLO11
Отвечает за загрузку модели и обработку кадров
"""

from ultralytics import YOLO  # type: ignore # Библиотека Ultralytics для работы с YOLO моделями
import cv2  # OpenCV для работы с изображениями
import os  # Для проверки существования файлов
from config import (
    MODEL_PATH,  # Путь к обученной модели
    YOLO_CONFIDENCE,  # Порог уверенности для фильтрации детекций
    YOLO_IMG_SIZE,  # Размер изображения для YOLO
    MSG_NO_MODEL,  # Сообщение об ошибке если модель не найдена
    SELECTION_COLOR,  # Цвет рамки при выборе области экрана (BGR формат для OpenCV)
    SELECTION_THICKNESS  # Толщина линии рамки при выборе области
)


class CardDetector:
    """
    Класс для детекции карт Clash Royale с помощью YOLO11

    Функционал:
    1. Загрузка обученной модели YOLO
    2. Обработка кадров и получение детекций
    3. Фильтрация детекций по уровню уверенности
    4. Возврат информации об обнаруженных объектах
    """

    def __init__(self, model_path=MODEL_PATH):
        """
        Инициализация детектора

        Args:
            model_path (str): Путь к файлу модели YOLO (.pt файл)
        """
        self.model_path = model_path  # Сохраняем путь к модели
        self.model = None  # Модель YOLO (загружается при вызове load_model)
        self.class_names = None  # Названия классов (карт) из модели

    def load_model(self):
        """
        Загрузка обученной модели YOLO из файла

        Returns:
            bool: True если модель успешно загружена, False если произошла ошибка
        """
        # Проверяем существование файла модели
        if not os.path.exists(self.model_path):
            print(MSG_NO_MODEL.format(self.model_path))
            return False

        try:
            # Загружаем модель YOLO
            print(f"Загрузка модели из: {self.model_path}")
            self.model = YOLO(self.model_path)

            # Получаем названия классов из модели
            # model.names - это словарь {0: "Giant", 1: "Arrows", ...}
            self.class_names = self.model.names

            print(f"Модель успешно загружена. Количество классов: {len(self.class_names)}")
            # print(f"Классы карт: {list(self.class_names.values())}")

            return True

        except Exception as e:
            print(f"ОШИБКА при загрузке модели: {e}")
            return False

    def detect(self, frame):
        """
        Обнаружение карт на кадре

        Args:
            frame (numpy.ndarray): Изображение в формате BGR (OpenCV)

        Returns:
            list: Список обнаруженных объектов, каждый объект - это словарь:
                  {
                      'class_id': int,      # ID класса (номер карты)
                      'class_name': str,    # Название карты
                      'confidence': float,  # Уверенность детекции (0-1)
                      'bbox': [x1, y1, x2, y2]  # Координаты bounding box
                  }
                  Возвращает пустой список если ничего не обнаружено
        """
        # Проверяем что модель загружена
        if self.model is None or self.class_names is None:
            print("ОШИБКА: Модель не загружена. Вызовите load_model() сначала.")
            return []

        # Проверяем что кадр не пустой
        if frame is None:
            print("ОШИБКА: Получен пустой кадр")
            return []

        try:
            # Запускаем инференс модели на кадре
            # verbose=False - отключаем вывод логов YOLO в консоль
            # imgsz - размер изображения для обработки (YOLO изменит размер автоматически)
            # conf - минимальный порог уверенности для детекций
            results = self.model.predict(
                source=frame,
                imgsz=YOLO_IMG_SIZE,
                conf=YOLO_CONFIDENCE,
                verbose=False
            )

            # Список для хранения обнаруженных объектов
            detections = []

            # Обрабатываем результаты
            # results[0] - результаты для первого (единственного) изображения
            for result in results:
                # result.boxes - объект содержащий все bounding boxes
                boxes = result.boxes

                # Если детекций нет, пропускаем
                if boxes is None or len(boxes) == 0:
                    continue

                # Проходим по каждой детекции
                for box in boxes:
                    # Извлекаем данные из детекции
                    # box.xyxy - координаты bounding box в формате [x1, y1, x2, y2]
                    # box.conf - уверенность детекции
                    # box.cls - ID класса

                    bbox = box.xyxy[0].cpu().numpy()  # Координаты (конвертируем из tensor в numpy)
                    confidence = float(box.conf[0].cpu().numpy())  # Уверенность
                    class_id = int(box.cls[0].cpu().numpy())  # ID класса

                    # Получаем название класса (карты)
                    class_name = self.class_names[class_id]

                    # Формируем словарь с информацией об объекте
                    detection = {
                        'class_id': class_id,
                        'class_name': class_name,
                        'confidence': confidence,
                        'bbox': bbox.tolist()  # [x1, y1, x2, y2]
                    }

                    # Добавляем в список обнаруженных объектов
                    detections.append(detection)

            return detections

        except Exception as e:
            print(f"ОШИБКА при детекции: {e}")
            return []

    def draw_detections(self, frame, detections):
        """
        Отрисовка bounding boxes и подписей на кадре (для визуализации)

        Args:
            frame (numpy.ndarray): Исходное изображение
            detections (list): Список детекций из метода detect()

        Returns:
            numpy.ndarray: Изображение с нарисованными детекциями
        """
        # Создаем копию кадра чтобы не изменять оригинал
        frame_copy = frame.copy()

        # Проходим по всем детекциям
        for det in detections:
            # Извлекаем данные
            bbox = det['bbox']  # [x1, y1, x2, y2]
            class_name = det['class_name']
            confidence = det['confidence']

            # Координаты bounding box (конвертируем в int для OpenCV)
            x1, y1, x2, y2 = map(int, bbox)

            # Рисуем прямоугольник вокруг объекта
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (SELECTION_COLOR), SELECTION_THICKNESS)

            # Формируем текст с названием и уверенностью
            label = f"{class_name} {confidence:.2f}"

            # Рисуем текст поверх фона
            cv2.putText(
                frame_copy,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),  # Черный цвет текста
                2
            )

        return frame_copy
