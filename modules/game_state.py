# 2.1. Создать modules/game_state.py
# Что: Глобальное состояние игры
# Переменные:
# log_screen (deque, maxlen=4) - последние 4 кадра
# timer_list (list) - все timer_obj
# ability_list (list) - все ability_obj
# spell_dict_time (dict) - наши заклинания с таймаутом
# spell_dict_list (dict) - отслеживание заклинаний в руке
# card_manager (CardManager) - менеджер карт
# elixir_balance (float) - эликсир противника
# game_start_time (float) - время начала игры
# elixir_speed_multiplier (float) - множитель скорости (1x, 2x, 3x)
# Методы:
# reset() - сброс состояния между боями
# add_frame(detections, timestamp) - добавить кадр в log_screen
# update_elixir(timestamp) - обновить эликсир по времени
# spend_elixir(amount) - списать эликсир