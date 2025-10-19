import sys
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import total_card as tc

total_card_list = [
                                    tc.Card_random,
                                    tc.Card_boss_bandit,
                                    tc.Card_bomb_tower,
                                    tc.Card_giant_snowball,
                                    tc.Card_rage,
                                    tc.Card_vines,
                                    tc.Card_the_log,
                                    tc.Card_skeleton,
                                    tc.Card_dark_prince,
                                    tc.Card_hunter,
                                    tc.Card_bandit,
                                    tc.Card_lumberjack,
                                    tc.Card_miner,
                                ]

cnt_card = len(total_card_list)
cnt_spell = sum(1 for card in total_card_list if card.spell)
cnt_champion = sum(1 for card in total_card_list if card.champion)
cnt_evolution = sum(1 for card in total_card_list if card.evolution)

print('----------------------------')
print(f"Количество карт:       {cnt_card:>3}")
print(f"Количество заклинаний: {cnt_spell:>3}")
print(f"Количество чемпионов:  {cnt_champion:>3}")
print(f"Количество эволюций:   {cnt_evolution:>3}")
