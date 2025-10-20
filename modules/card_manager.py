# -*- coding: utf-8 -*-
"""
Менеджер для управления циклом карт противника

Управляет:
- deck_cards: множество всех доступных карт (121 карта)
- await_cards: очередь из 4 карт в ожидании (слева на панели)
- hand_cards: список из 4 карт в руке противника (справа на панели)
"""

import sys
from pathlib import Path
from typing import Optional, List
import copy

# Добавляем корневую папку проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.classes import Card
from modules import all_card


class CardManager:
    """
    Класс для управления циклом карт противника

    Attributes:
        deck_cards (set): Множество всех доступных карт (уменьшается по мере открытия)
        await_cards (list): Очередь из 4 карт в ожидании
        hand_cards (list): Список из 4 карт в руке
    """

    def __init__(self):
        """
        Инициализация менеджера карт.
        Создает deck_cards со всеми 121 картами.
        Заполняет await_cards и hand_cards карточками-заглушками card_random.
        """
        # Собираем все карты из total_card.py в множество (кроме Card_random)
        self.deck_cards = set()

        # Получаем все атрибуты из модуля total_card
        for attr_name in dir(all_card):
            # Ищем только переменные начинающиеся с "Card_" (но не Card_random)
            if attr_name.startswith('Card_') and attr_name != 'Card_random':
                card = getattr(all_card, attr_name)
                # Проверяем что это экземпляр класса Card
                if isinstance(card, Card):
                    # Создаем глубокую копию карты
                    self.deck_cards.add(copy.deepcopy(card))

        # Инициализируем await_cards и hand_cards заглушками
        self.await_cards = [self.card_random() for _ in range(4)]
        self.hand_cards = [self.card_random() for _ in range(4)]


    def card_random(self) -> Card:
        """
        Создает карту-заглушку для неизвестных карт противника.

        Returns:
            Card: Карта со знаком вопроса (Card_random)
        """
        return copy.deepcopy(all_card.Card_random)


    def play_new_card(self, class_name: str) -> bool:
        """
        Обрабатывает разыгрывание НОВОЙ (ранее неизвестной) карты противником.

        Логика:
        1. Удаляем крайнюю левую card_random из hand_cards
        2. На освободившееся место ставим крайнюю правую карту из await_cards
        3. Смещаем оставшиеся карты в await_cards вправо
        4. На первую позицию в await_cards ставим новую определенную карту
        5. Удаляем эту карту из deck_cards

        Args:
            class_name: класс новой карты которую сыграл противник

        Returns:
            bool: True если успешно, False если что-то пошло не так
        """
        # Ищем карту в deck_cards по class_name
        found_card = None
        for card in self.deck_cards:
            if card.class_name == class_name:
                found_card = card
                break

        # Проверяем что карта есть в deck_cards
        if found_card is None:
            print(f"⚠ ОШИБКА: Карта {class_name} не найдена в deck_cards")
            return False

        # Ищем первый card_random в hand_cards (крайний левый)
        random_index = None
        for i, hand_card in enumerate(self.hand_cards):
            if hand_card.name == "Card Random":
                random_index = i
                break

        if random_index is None:
            print("⚠ ОШИБКА: Не найдено card_random в hand_cards для замены")
            return False

        # 1. Удаляем крайнюю левую card_random из hand_cards
        self.hand_cards.pop(random_index)

        # 2. На освободившееся место ставим крайнюю правую карту из await_cards (индекс 3)
        moved_card = self.await_cards.pop(3)
        self.hand_cards.insert(random_index, moved_card)

        # 3. Смещаем оставшиеся карты в await_cards вправо (они уже сдвинулись после pop)
        # await_cards теперь имеет 3 элемента [0,1,2]

        # 4. На первую позицию в await_cards ставим новую карту
        self.await_cards.insert(0, copy.deepcopy(found_card))

        # 5. Удаляем карту из deck_cards
        self.deck_cards.discard(found_card)

        return True


    def play_known_card(self, class_name: str) -> bool:
        """
        Обрабатывает разыгрывание ИЗВЕСТНОЙ карты из руки противника.

        Логика:
        1. Находим и удаляем карту из hand_cards
        2. На освободившееся место ставим крайнюю правую карту из await_cards
        3. Смещаем оставшиеся карты в await_cards вправо
        4. На первую позицию в await_cards ставим карту которую удалили из hand_cards

        Args:
            class_name: класс известной карты которую сыграл противник

        Returns:
            bool: True если успешно, False если карты нет в руке
        """
        # Ищем карту в hand_cards по class_name
        card_index = None
        for i, hand_card in enumerate(self.hand_cards):
            if hand_card.class_name == class_name:
                card_index = i
                break

        if card_index is None:
            print(f"⚠ ОШИБКА: Карта {class_name} не найдена в hand_cards")
            return False

        # 1. Удаляем карту из hand_cards
        played_card = self.hand_cards.pop(card_index)

        # 2. На освободившееся место ставим крайнюю правую карту из await_cards
        moved_card = self.await_cards.pop(3)
        self.hand_cards.insert(card_index, moved_card)

        # 3. Смещение произошло автоматически после pop

        # 4. На первую позицию в await_cards ставим сыгранную карту
        self.await_cards.insert(0, played_card)

        return True


    def get_hand_cards(self) -> List[Card]:
        """
        Возвращает список карт в руке противника.

        Returns:
            List[Card]: Копия списка hand_cards
        """
        return self.hand_cards.copy()


    def get_await_cards(self) -> List[Card]:
        """
        Возвращает список карт в ожидании.

        Returns:
            List[Card]: Копия списка await_cards
        """
        return self.await_cards.copy()


    def is_card_in_hand(self, class_name: str) -> bool:
        """
        Проверяет наличие карты в руке по class_name.

        Args:
            class_name: Название класса для поиска

        Returns:
            bool: True если карта найдена в hand_cards
        """
        for card in self.hand_cards:
            if card.class_name == class_name:
                return True
        return False


    def is_card_in_await(self, class_name: str) -> bool:
        """
        Проверяет наличие карты в ожидании по class_name.

        Args:
            class_name: Название класса для поиска

        Returns:
            bool: True если карта найдена в await_cards
        """
        for card in self.await_cards:
            if card.class_name == class_name:
                return True
        return False


    def find_card_in_deck(self, class_name: str) -> Optional[Card]:
        """
        Ищет карту в deck_cards по class_name.

        Args:
            class_name: Название класса для поиска

        Returns:
            Optional[Card]: Найденная карта или None если не найдена
        """
        for card in self.deck_cards:
            if card.class_name == class_name:
                return card
        return None


    def get_deck_size(self) -> int:
        """
        Возвращает количество оставшихся неизвестных карт в колоде.

        Returns:
            int: Размер deck_cards
        """
        return len(self.deck_cards)


    def count_card_random_in_hand(self) -> int:
        """
        Подсчитывает количество card_random в hand_cards.
        Используется для определения сколько карт еще неизвестно.

        Returns:
            int: Количество заглушек в руке
        """
        count = 0
        for card in self.hand_cards:
            if card.name == "Card Random":
                count += 1
        return count


    def reset(self):
        """
        Сбрасывает состояние менеджера (для начала нового боя).
        Восстанавливает все карты в deck_cards.
        Заполняет await_cards и hand_cards заглушками.
        """
        self.__init__()


    def __repr__(self) -> str:
        """
        Строковое представление для отладки.
        """
        hand_names = [c.name for c in self.hand_cards]
        await_names = [c.name for c in self.await_cards]
        return (f"CardManager(\n"
                f"  deck_size={len(self.deck_cards)},\n"
                f"  await={await_names},\n"
                f"  hand={hand_names}\n"
                f")")
