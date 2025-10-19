import sys
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.classes import Card


# Неизвестная карта
Card_random = Card(
                        name="Card Random",
                        image_path="data/card_random.png",
                        elixir=0,
                        class_name=None,
                        spell=False,
                        spell_time=None,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )


# Карта Босс Бандит
Card_boss_bandit = Card(
                        name="Boss Bandit",
                        image_path="data/card_boss_bandit.png",
                        elixir=6,
                        class_name=".WC boss bandit",
                        spell=False,
                        spell_time=None,
                        champion=True,
                        ability_class_name="AC boss bandit",
                        ability_elixir=1,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )

# Карта Башня бомбежка
Card_bomb_tower = Card(
                        name="Bomb Tower",
                        image_path="data/card_bomb_tower.png",
                        elixir=4,
                        class_name="BR bomb tower",
                        spell=False,
                        spell_time=None,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )

# Карта Снежок
Card_giant_snowball = Card(
                        name="Giant Snowball",
                        image_path="data/card_giant_snowball.png",
                        elixir=2,
                        class_name="SС giant snowball",
                        spell=True,
                        spell_time=5,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=True,
                        evolution_image_path="data/card_giant_snowball_evo.png",
                        cnt_evo=0,
                        target_evo=2
                        )

# Карта Ярость
Card_rage  = Card(
                        name="Rage",
                        image_path="data/card_rage.png",
                        elixir=2,
                        class_name="SE rage",
                        spell=True,
                        spell_time=5,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )

# Карта Лоза
Card_vines  = Card(
                        name="Vines",
                        image_path="data/card_vines.png",
                        elixir=3,
                        class_name="SE vines ",
                        spell=True,
                        spell_time=5,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )

# Карта Бревно
Card_the_log   = Card(
                        name="The Log",
                        image_path="data/card_the_log.png",
                        elixir=2,
                        class_name="SL the log ",
                        spell=True,
                        spell_time=5,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )

# Карта Скелеты
# после внесения правок в RoboFlow, переименовать skeleton -> skeletons (!!!)
Card_skeleton  = Card(
                        name="Skeleton",
                        image_path="data/card_skeleton.png",
                        elixir=1,
                        class_name="WC skeleton",
                        spell=False,
                        spell_time=None,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )

# Карта Темный принц
Card_dark_prince = Card(
                        name="Dark Prince",
                        image_path="data/card_dark_prince.png",
                        elixir=4,
                        class_name="WE dark prince",
                        spell=False,
                        spell_time=None,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )

# Карта Охотник
Card_hunter = Card(
                        name="Hunter",
                        image_path="data/card_hunter.png",
                        elixir=4,
                        class_name="WE hunter",
                        spell=False,
                        spell_time=None,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )

# Карта Бандитка
Card_bandit = Card(
                        name="Bandit",
                        image_path="data/card_bandit.png",
                        elixir=3,
                        class_name="WL bandit",
                        spell=False,
                        spell_time=None,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )

# Карта Дровосек
Card_lumberjack = Card(
                        name="Lumberjack",
                        image_path="data/card_lumberjack.png",
                        elixir=4,
                        class_name="WL lumberjack",
                        spell=False,
                        spell_time=None,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=True,
                        evolution_image_path="data/card_lumberjack_evo.png",
                        cnt_evo=0,
                        target_evo=2
                        )

# Карта Шахтер
Card_miner = Card(
                        name="Miner",
                        image_path="data/card_miner.png",
                        elixir=3,
                        class_name="WL miner",
                        spell=False,
                        spell_time=None,
                        champion=False,
                        ability_class_name=None,
                        ability_elixir=0,
                        evolution=False,
                        evolution_image_path=None,
                        cnt_evo=0,
                        target_evo=0
                        )
