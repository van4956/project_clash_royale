"""
Координатор всех обработчиков детекций.
Главная функция process_detections вызывается из главного цикла app.py.
Координирует работу timer_processor, spell_processor, ability_processor, evolution_processor.
"""

from typing import List, Dict, Any
from modules.game_state import GameState
from modules.classes import Card
from modules import timer_processor
from modules import spell_processor
from modules import ability_processor
from modules import evolution_processor


def process_detections(
    all_detections: List[Dict[str, Any]],
    current_time: float,
    game_state: GameState,
    all_cards: List[Card]
) -> Dict[str, Any]:
    """
    Главная функция координатор для обработки детекций текущего кадра.

    Args:
        all_detections: список всех детекций текущего кадра
        current_time: временная метка текущего кадра
        game_state: объект глобального состояния игры
        all_cards: список всех карт для поиска атрибутов

    Returns:
        dict: результаты обработки {
            'elixir_spent_timer': float,
            'elixir_spent_spell': float,
            'elixir_spent_ability': float,
            'total_elixir_spent': float,
        }

    Последовательность обработки:
        1. Добавление кадра в log_screen
        2. Cleanup хвостов всех списков и словарей
        3. Обработка эволюционных маркеров (независимый процесс)
        4. Обработка красных таймеров (если есть _timer_red)
        5. Обработка заклинаний (всегда)
        6. Обработка абилок чемпионов (если есть абилки)
        7. Обновление баланса эликсира противника
        8. Возврат результатов
    """
    # 1. Добавляем кадр в историю детекций
    game_state.add_frame(all_detections, current_time)

    # Инициализируем результаты
    results = {
        'elixir_spent_timer': 0.0,
        'elixir_spent_spell': 0.0,
        'elixir_spent_ability': 0.0,
        'total_elixir_spent': 0.0,
    }

    # 2. Cleanup хвостов всех списков и словарей
    _cleanup_all(game_state)

    # 3. Обработка эволюционных маркеров
    # Независимая от других процессов, только фиксация маркеров
    # Обновление cnt_evo происходит в card_manager.play_known_card/play_new_card
    evolution_processor.process_evolution_detections(
        all_detections,
        game_state.evolution_dict_timer,
        current_time
    )

    # 4. Обработка красных таймеров (если есть _timer_red)
    if _has_red_timers(all_detections):
        elixir_spent_timer = timer_processor.process_timer_detections(
            game_state.log_screen,
            game_state.timer_list,
            game_state.card_manager,
            all_detections,
            current_time,
            game_state.evolution_dict_timer
        )
        results['elixir_spent_timer'] = elixir_spent_timer

    # 5. Обработка заклинаний (всегда запускается)
    elixir_spent_spell = spell_processor.process_spell_detections(
        all_detections,
        game_state.spell_dict_hand,
        game_state.spell_dict_our,
        game_state.spell_dict_enemy,
        game_state.card_manager,
        current_time,
        all_cards
    )
    results['elixir_spent_spell'] = elixir_spent_spell

    # 6. Обработка абилок чемпионов (всегда запускается, внутри фильтр)
    elixir_spent_ability = ability_processor.process_ability_detections(
        all_detections,
        game_state.ability_dict_enemy,
        current_time,
        all_cards
    )
    results['elixir_spent_ability'] = elixir_spent_ability

    # 7. Подсчет общего потраченного эликсира
    total_elixir_spent = (
        results['elixir_spent_timer'] +
        results['elixir_spent_spell'] +
        results['elixir_spent_ability']
    )
    results['total_elixir_spent'] = total_elixir_spent

    # 8. Обновление баланса эликсира противника
    game_state.update_elixir(current_time, total_elixir_spent)

    # 9. Обновление time_screen
    game_state.time_screen = current_time

    return results


def _cleanup_all(game_state: GameState) -> None:
    """
    Очистка хвостов всех списков и словарей (сдвиг скользящих окон).

    Args:
        game_state: объект глобального состояния игры

    Логика:
        - timer_list: удаление последнего элемента из каждого timer_obj
        - spell_dict_hand: удаление последнего элемента из каждого списка
        - Остальные словари (our/enemy) очищаются по таймаутам внутри своих процессоров
    """
    # Cleanup timer_list
    timer_processor.cleanup_timers(game_state.timer_list)

    # Cleanup spell_dict_hand (скользящее окно)
    spell_processor.cleanup_spell_dict_hand(game_state.spell_dict_hand)


def _has_red_timers(all_detections: List[Dict[str, Any]]) -> bool:
    """
    Проверяет наличие красных таймеров в детекциях.

    Args:
        all_detections: список всех детекций текущего кадра

    Returns:
        bool: True если есть хотя бы один _timer_red
    """
    for detection in all_detections:
        class_name = detection.get('class_name', '')
        if class_name == '_timer_red':
            return True
    return False
