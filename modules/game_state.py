# 2.1. Создать modules/game_state.py
# Глобальное состояние игры
# Переменные:
# log_screen (deque, maxlen=4) - последние 4 кадра
# timer_list (list) - все timer_obj
# ability_list (list) - все ability_obj
# spell_dict_time (dict) - наши заклинания с таймаутом
# spell_dict_list (dict) - отслеживание заклинаний в руке
# card_manager (CardManager) - менеджер карт
# elixir_balance (float) - эликсир противника
# game_start_time (float) - время начала игры
# Методы:
# reset() - сброс состояния между боями, при отлове определенного класса от модели детекции (_finish)
# add_frame(detections, timestamp) - добавить кадр в log_screen
# update_elixir(timestamp) - обновить эликсир по времени
# подсчет эликсира по формуле:
# if detected_class == "_elixir_x2":
#     elixir_rate = 2.0
# elif detected_class == "_elixir_x3":
#     elixir_rate = 3.0
# time_screen = <hh:mm:ss> # время детекции
# elixir_speed = 0.35 # количество элека за 1 секунда
# elixir_spent = 0  # потраченный эликсир, получаем по атрибуту из класса сыгранной карты
# elixir_rate = 1  # меняем в зависимости от полученного класса модели: _elixir_х2, _elixir_х3
# delta_time = current_time - time_screen # время между текущей и прошлой итерацией, в идеале 0.250мс, но могут быть смещения
# elixir_balance = max(0, min(10, elixir_balance (прошлый баланс) + delta_time * elixir_speed * elixir_rate - elixir_spent))