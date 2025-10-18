from dataclasses import dataclass

@dataclass
class TimerScreen(list):
    '''
    Класс для timer_screen
    Принимает массив массивов [[box_timer],[box_zone],[[box_lvl],[box_lvl],],[class_name, class_name,]]
    Доступны дополнительные атрибуты: first_screen, last_screen, list_ignore
    '''
    first_screen: int | None = None # время первой детекции box_timer
    last_screen: int | None = None # время последней детекции box_timer
    list_ignore: list[int] | None = None # список class_name которые игнорировать


@dataclass
class Card():
    '''
    Класс для карт Clash Royale
    '''
    name: str # название (реальное на анг)
    image_path: str # ссылка на картинку в проекте
    elixir: int # стоимость карты (число элика)
    class_name: str # список классов class_name которые детектит модель
    champion: bool # Champion (true/false)
    ability_class_name: str | None # абилка (class_name/none)
    ability_elixir: int # стоимость абалики (число элика/0)
    evolution: bool # Evolution (true/false)
    evolution_image_path: str | None # ссылка на картинку ево карты
    cnt_evo: int = 0 # счетчик эво маркеров
    target_evo: int = 0 # количество эво маркеров нужное для активации эволюции
