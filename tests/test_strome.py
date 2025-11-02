"""Test Strome's scoring to find the bug"""
from data_fetch import NHLDataFetcher
from scoring import FantasyScorer
import json

# Initialize
fetcher = NHLDataFetcher()
scorer = FantasyScorer()

# Load player data
print("Loading player data from cache...")
import os
cache_file = os.path.join(fetcher.cache_dir, "player_8479318.json")  # Ryan Strome's ID

if os.path.exists(cache_file):
    with open(cache_file, 'r', encoding='utf-8') as f:
        strome_data = json.load(f)
else:
    print("Fetching Strome from API...")
    import requests
    response = requests.get('https://api-web.nhle.com/v1/player/8479318/landing')
    strome_data = response.json()

# Create player object as main.py would
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
print("RYAN STROME ANALYSIS")
print("="*80)

# Check what stats we have
print("\nSeason Totals:")
for season in player.get('seasonTotals', []):
    if season.get('leagueAbbrev') == 'NHL' and season.get('gameTypeId') == 2:
        print(f"  Season {season.get('season')}: {season.get('gamesPlayed')} GP, {season.get('goals')} G, {season.get('assists')} A")

print("\nFeatured Stats:")
if 'featuredStats' in player and 'regularSeason' in player['featuredStats']:
    if 'subSeason' in player['featuredStats']['regularSeason']:
        sub = player['featuredStats']['regularSeason']['subSeason']
        print(f"  Current: {sub.get('gamesPlayed')} GP, {sub.get('goals')} G, {sub.get('assists')} A")

# Extract combined stats
print("\n" + "="*80)
print("COMBINED STATS EXTRACTION")
print("="*80)
combined_stats = scorer._extract_combined_stats(player)
print(f"\nGames Played: {combined_stats.get('gamesPlayed')}")
print(f"Goals: {combined_stats.get('goals')}")
print(f"Assists: {combined_stats.get('assists')}")
print(f"Points: {combined_stats.get('points')}")

# Calculate fantasy points
print("\n" + "="*80)
print("FANTASY POINTS CALCULATION")
print("="*80)
fantasy_points = scorer.calculate_points(player)
print(f"\nTotal Fantasy Points: {fantasy_points:.1f}")

# Get breakdown
print("\n" + "="*80)
print("SCORING BREAKDOWN")
print("="*80)
breakdown = scorer.generate_scoring_breakdown(player)
print(breakdown)
