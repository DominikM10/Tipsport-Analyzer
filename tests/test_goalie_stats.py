"""Test goalie stats extraction"""
from scoring import FantasyScorer
import requests
import json

# Fetch Varlamov's data directly from API
response = requests.get('https://api-web.nhle.com/v1/player/8476883/landing')
varlamov_data = response.json()

# Create a player object as main.py would
player = {
    'id': 8476883,
    'name': 'Semyon Varlamov',
    'position': 'G',
    'team': 'NYI',
    'featuredStats': varlamov_data.get('featuredStats', {}),
    'seasonTotals': varlamov_data.get('seasonTotals', []),
    'careerTotals': varlamov_data.get('careerTotals', {})
}

# Add legacy keys
if 'featuredStats' in varlamov_data and 'regularSeason' in varlamov_data['featuredStats']:
    if 'subSeason' in varlamov_data['featuredStats']['regularSeason']:
        player['stats'] = varlamov_data['featuredStats']['regularSeason']['subSeason']
        player['current_season_stats'] = varlamov_data['featuredStats']['regularSeason']['subSeason']

# Now test the scoring
scorer = FantasyScorer()

print("="*80)
print("VARLAMOV TEST")
print("="*80)

# Extract combined stats
combined_stats = scorer._extract_combined_stats(player)
print(f"\nCombined Stats:")
print(json.dumps(combined_stats, indent=2))

# Calculate fantasy points
fantasy_points = scorer.calculate_points(player)
print(f"\nFantasy Points: {fantasy_points}")

# Check what the goalie scoring method returns
goalie_points = scorer._calculate_goalie_points(combined_stats)
print(f"Goalie Points: {goalie_points}")
