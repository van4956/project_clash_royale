"""
Модуль для управления глобальным состоянием игры.
Хранит все данные о текущем бою: кадры детекции, таймеры, заклинания, баланс эликсира.
"""

from collections import deque
from typing import List, Dict, Optional
from modules.card_manager import CardManager


class GameState:
    """
    Менеджер глобального состояния игры.
    Хранит все данные о текущем бою и предоставляет методы для их обновления.
    """

    # Константа скорости набора эликсира (эликсир/сек при x1)
    ELIXIR_SPEED = 0.35

    def __init__(self):
        """Инициализация состояния игры."""
        # Хранение кадров детекции
        self.log_screen = deque(maxlen=4)  # последние 4 кадра с детекциями

        # Хранение объектов
        self.timer_list: List = []  # все активные TimerObject

        # Словари для заклинаний
        self.spell_dict_hand: Dict[str, List[int]] = {}  # НАША рука: {"ZE_rage": [1,0,0,0]}
        self.spell_dict_our: Dict[str, List[float]] = {}  # НАШИ активные: {"SE_rage": [timeout_1, timeout_2]}
        self.spell_dict_enemy: Dict[str, List[float]] = {}  # ВРАЖЕСКИЕ активные: {"SE_rage": [timeout_1]}

        # Словарь для абилок чемпионов
        self.ability_dict_enemy: Dict[str, float] = {}  # ВРАЖЕСКИЕ активные абилки: {"AC_xxx": timeout_end}

        # Словарь для маркеров эволюции
        self.evolution_dict_timer: Dict[float, str] = {}  # Маркеры эво: {timestamp: "detect"/"record"}

        # Менеджер карт оппонента
        self.card_manager = CardManager()

        # Эликсир оппонента
        self.elixir_balance: float = 5.0  # начальный баланс
        self.elixir_rate: float = 1.0  # множитель скорости (1.0, 2.0, 3.0)
        self.elixir_spent: float = 0.0  # эликсир потраченный в текущей итерации

        # Метрики эликсира (для отладки/валидации)
        self.elixir_negative: float = 0.0  # сумма эликсира ушедшего в минус
        self.elixir_stagnation: float = 0.0  # простаиваемый эликсир выше 10

        # Временные метки
        self.game_start_time: Optional[float] = None  # время начала боя
        self.time_screen: Optional[float] = None  # время последней обработки кадра

    def reset(self):
        """
        Сброс состояния между боями.
        Вызывается при обнаружении класса _finish от модели детекции.
        """
        self.log_screen.clear()
        self.timer_list.clear()
        self.spell_dict_hand.clear()
        self.spell_dict_our.clear()
        self.spell_dict_enemy.clear()
        self.ability_dict_enemy.clear()
        self.evolution_dict_timer.clear()
        self.card_manager.reset()

        self.elixir_balance = 5.0
        self.elixir_rate = 1.0
        self.elixir_spent = 0.0
        self.elixir_negative = 0.0
        self.elixir_stagnation = 0.0

        self.game_start_time = None
        self.time_screen = None

    def add_frame(self, detections: List, timestamp: float):
        """
        Добавить кадр детекции в историю.

        Args:
            detections: список детекций с текущего кадра
            timestamp: временная метка кадра
        """
        self.log_screen.append({
            'detections': detections,
            'timestamp': timestamp
        })

    def set_elixir_rate(self, class_name: str):
        """
        Установить множитель скорости набора эликсира.

        Args:
            class_name: класс детекции (_elixir_x2 или _elixir_x3)
        """
        if class_name == "_elixir_x2":
            self.elixir_rate = 2.0
        elif class_name == "_elixir_x3":
            self.elixir_rate = 3.0
        else:
            self.elixir_rate = 1.0

    def update_elixir(self, current_time: float, elixir_spent: float = 0.0):
        """
        Обновить баланс эликсира по времени и потраченному эликсиру.

        Формула:
        1. elixir_balance = min(10, prev_balance + delta_time * elixir_speed * elixir_rate - elixir_spent)
        2. if elixir_balance < 0: elixir_negative += abs(elixir_balance); elixir_balance = 0
        3. if elixir_balance > 10: elixir_stagnation += abs(elixir_balance); elixir_balance = 10

        Args:
            current_time: текущая временная метка
            elixir_spent: эликсир потраченный на карты в текущей итерации
        """
        # Первая итерация - просто сохраняем время
        if self.time_screen is None:
            self.time_screen = current_time
            return

        # Вычисляем delta_time
        delta_time = current_time - self.time_screen

        # Вычисляем накопленный эликсир
        gained_elixir = delta_time * self.ELIXIR_SPEED * self.elixir_rate

        # Вычисляем новый баланс
        self.elixir_balance = min(10.0, self.elixir_balance + gained_elixir - elixir_spent)

        # Считаем простаиваемый баланс эликсира выше 10
        if self.elixir_balance > 10.0:
            self.elixir_stagnation += (self.elixir_balance - 10.0)
            self.elixir_balance = 10.0

        # Проверяем уход в negative
        if self.elixir_balance < 0:
            self.elixir_negative += abs(self.elixir_balance)
            self.elixir_balance = 0.0

        # Обновляем время последней обработки
        self.time_screen = current_time

    def get_elixir_metrics(self) -> Dict[str, float]:
        """
        Получить метрики эликсира для мониторинга.

        Returns:
            Словарь с метриками {balance, rate, negative, stagnation}
        """
        return {
            'balance': self.elixir_balance,
            'rate': self.elixir_rate,
            'negative': self.elixir_negative,
            'stagnation': self.elixir_stagnation
        }

    def __repr__(self) -> str:
        """Строковое представление состояния."""
        return (
            f"GameState(elixir={self.elixir_balance:.2f}x{self.elixir_rate}, "
            f"timers={len(self.timer_list)}, "
            f"frames={len(self.log_screen)})"
        )
