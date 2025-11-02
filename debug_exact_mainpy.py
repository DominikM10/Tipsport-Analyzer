"""Comprehensive debugging of Strome calculation"""
from scoring import FantasyScorer
import json

scorer = FantasyScorer()

# Load Strome
with open('cache/player_8479318.json', 'r', encoding='utf-8') as f:
    strome_data = json.load(f)

# Create player EXACTLY as main.py does (line 216-231)
player = {
    'id': 8479318,
    'name': 'Ryan Strome',
    'firstName': 'Ryan',
    'lastName': 'Strome',
    'sweaterNumber': 16,
    'position': 'C',
    'headshot': 'https://assets.nhle.com/mugs/nhl/20252026/ANA/8479318.png',
    'team': 'ANA',
    'birth_date': '1993-07-11',
    'height_cm': 185,
    'weight_kg': 91,
    'nationality': 'CAN'
}

# Main.py merges the full data (lines 224-227)
player.update({
    'featuredStats': strome_data.get('featuredStats', {}),
    'seasonTotals': strome_data.get('seasonTotals', []),
    'careerTotals': strome_data.get('careerTotals', {})
})

# Main.py ALSO sets player['stats'] (line 231)
if 'featuredStats' in strome_data and 'regularSeason' in strome_data['featuredStats']:
    if 'subSeason' in strome_data['featuredStats']['regularSeason']:
        player['stats'] = strome_data['featuredStats']['regularSeason']['subSeason']
        player['current_season_stats'] = strome_data['featuredStats']['regularSeason']['subSeason']

print("="*80)
print("EXACT MAIN.PY SCENARIO")
print("="*80)

print("\nPlayer keys:", list(player.keys()))
print(f"\nplayer['stats'] exists: {'stats' in player}")
if 'stats' in player:
    print(f"  Games in player['stats']: {player['stats'].get('gamesPlayed')}")
    print(f"  Goals in player['stats']: {player['stats'].get('goals')}")

print(f"\nplayer['seasonTotals'] length: {len(player.get('seasonTotals', []))}")

print("\n" + "-"*80)
print("CALLING _extract_combined_stats")
print("-"*80)

combined = scorer._extract_combined_stats(player)

print(f"\nResult:")
print(f"  Games: {combined.get('gamesPlayed'):.2f}")
print(f"  Goals: {combined.get('goals'):.2f}")
print(f"  Assists: {combined.get('assists'):.2f}")

print("\n" + "-"*80)
print("CALLING calculate_points")
print("-"*80)

fp = scorer.calculate_points(player)
print(f"\nFantasy Points: {fp:.1f}")

# Now add fantasy_points to player like main.py does
player['fantasy_points'] = fp

# And try the breakdown
print("\n" + "-"*80)
print("BREAKDOWN")
print("-"*80)
breakdown = scorer.generate_scoring_breakdown(player)
for line in breakdown.split('\n'):
    if 'Goals' in line or 'Assists' in line or 'TOTAL' in line:
        print(line)
