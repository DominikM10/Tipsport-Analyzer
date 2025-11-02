"""Check if Strome has separate stats in cache vs API"""
import json
import os

cache_file = "cache/player_8479318.json"

if os.path.exists(cache_file):
    with open(cache_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("Season Totals in cache:")
    for season in data.get('seasonTotals', []):
        if season.get('leagueAbbrev') == 'NHL' and season.get('gameTypeId') == 2:
            print(f"  {season.get('season')}: {season.get('gamesPlayed')} GP, "
                  f"{season.get('goals')} G, {season.get('assists')} A, "
                  f"PIM: {season.get('pim')}")
    
    print("\nFeatured Stats:")
    if 'featuredStats' in data:
        reg = data['featuredStats'].get('regularSeason', {})
        if 'subSeason' in reg:
            sub = reg['subSeason']
            print(f"  Current: {sub.get('gamesPlayed')} GP, "
                  f"{sub.get('goals')} G, {sub.get('assists')} A, "
                  f"PIM: {sub.get('pim')}")
