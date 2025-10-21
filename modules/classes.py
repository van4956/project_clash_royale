from dataclasses import dataclass



@dataclass
class TimerObject(list):
    '''
    Класс для timer_obj
    Принимает массив массивов [[timer_screen],[timer_screen],[timer_screen],
                               [timer_screen],[timer_screen],[timer_screen]]
    Создаем дополнительные атрибуты: first_screen, last_screen, list_ignore
    '''
    first_screen: int | None = None # время первой детекции box_timer
    last_screen: int | None = None # время последней детекции box_timer
    list_ignore: list[int] | None = None # список class_name которые игнорировать

    def del_last(self):
        '''Удаляет последний элемент из timer_obj (списка)        '''
        if len(self) > 0:
            self.pop()

    def add_full(self, timer_screen: list):
        '''Добавляет элемент спереди'''
        self.insert(0, [timer_screen])



@dataclass
class Card():
    '''
    Класс для карт Clash Royale
    '''
    card_id: int # уникальный id карты который мы получаем от модели
    card_name: str # название карты (реальное на английском)
    image_path: str # ссылка на картинку в проекте
    elixir: int # стоимость карты (число элика)
    class_name: str | None  # class_name которые детектит модель
    spell: bool # является ли заклинанием (true/false)
    spell_life_time: int | None # время исполнения заклинания (число сек)
    spell_my_hand_class_name: str | None # class_name которые детектит модель если это заклинание в НАШЕЙ руке
    champion: bool # Champion (true/false)
    ability_class_name: str | None # абилка (class_name/none)
    ability_elixir: int # стоимость абалики (число элика/0)
    evolution: bool # Evolution (true/false)
    evolution_image_path: str | None # ссылка на картинку ево карты
    cnt_evo: int = 0 # счетчик эво маркеров
    target_evo: int = 0 # количество эво маркеров нужное для активации эволюции
