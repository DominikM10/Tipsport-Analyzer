"""Debug main.py scoring flow for Strome"""
from data_fetch import NHLDataFetcher
from scoring import FantasyScorer
import json
import os

# Initialize
fetcher = NHLDataFetcher()
scorer = FantasyScorer()

# Load Strome from cache
cache_file = "cache/player_8479318.json"
with open(cache_file, 'r', encoding='utf-8') as f:
    strome_data = json.load(f)

# Create player object like main.py does
player = {
    'id': 8479318,
    'name': 'Ryan Strome',
    'position': 'F',
    'team': 'ANA',
    'cena': 9.8,
    'featuredStats': strome_data.get('featuredStats', {}),
    'seasonTotals': strome_data.get('seasonTotals', []),
    'careerTotals': strome_data.get('careerTotals', {})
}

print("="*80)
print("MAIN.PY SCORING FLOW DEBUG")
print("="*80)

# Step 1: Extract stats
print("\nStep 1: _extract_combined_stats")
stats = scorer._extract_combined_stats(player)
print(f"  Games: {stats.get('gamesPlayed'):.1f}")
print(f"  Goals: {stats.get('goals'):.1f}")
print(f"  Assists: {stats.get('assists'):.1f}")

# Step 2: Calculate fantasy points
print("\nStep 2: calculate_points")
fp = scorer.calculate_points(player)
print(f"  Fantasy Points: {fp:.1f}")

# Step 3: Store in player object
player['fantasy_points'] = fp
player['stats'] = stats

# Step 4: Show stats like main.py does
print("\nStep 3: Display in main.py (line 575)")
stats_display = scorer._extract_combined_stats(player)
goals_display = scorer._get_stat(stats_display, 'goals', 'g')
assists_display = scorer._get_stat(stats_display, 'assists', 'a')
games_display = scorer._get_stat(stats_display, 'gamesPlayed', 'games', 'gp')
print(f"  Games: {int(games_display)}")
print(f"  Goals: {int(goals_display)}")
print(f"  Assists: {int(assists_display)}")

# Step 5: Generate breakdown
print("\nStep 4: generate_scoring_breakdown")
breakdown = scorer.generate_scoring_breakdown(player)
# Just show the key parts
for line in breakdown.split('\n'):
    if 'Goals:' in line or 'Assists:' in line or 'TOTAL' in line:
        print(f"  {line}")
