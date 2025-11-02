"""Debug script to check goalie filtering"""
from data_fetch import NHLDataFetcher
from scoring import FantasyScorer
import json
import os
import requests

# Fetch data
fetcher = NHLDataFetcher()
players = fetcher.fetch_all_players()

print(f"\n🔄 Enhancing {len(players)} players with detailed stats...")

# Enhance with detailed stats (same as main.py does)
enhanced_players = []
for i, player in enumerate(players):
    player_id = player.get('id')
    if player_id:
        if i % 50 == 0:
            print(f"  Processing players {i+1}-{min(i+50, len(players))}/{len(players)}...")
        
        try:
            # Try cache first
            cache_file = os.path.join(fetcher.cache_dir, f"player_{player_id}.json")
            full_player_data = None
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        full_player_data = json.load(f)
                except:
                    pass
            
            # If not in cache, fetch it
            if not full_player_data:
                try:
                    url = f"{fetcher.base_url}/player/{player_id}/landing"
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    full_player_data = response.json()
                    # Cache it
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(full_player_data, f, ensure_ascii=False, indent=2)
                except:
                    continue
            
            # Merge stats structures
            if full_player_data:
                if 'featuredStats' in full_player_data:
                    player['featuredStats'] = full_player_data['featuredStats']
                if 'seasonTotals' in full_player_data:
                    player['seasonTotals'] = full_player_data['seasonTotals']
                if 'careerTotals' in full_player_data:
                    player['careerTotals'] = full_player_data['careerTotals']
                
                # Add legacy keys for compatibility
                if 'featuredStats' in full_player_data and 'regularSeason' in full_player_data['featuredStats']:
                    if 'subSeason' in full_player_data['featuredStats']['regularSeason']:
                        player['stats'] = full_player_data['featuredStats']['regularSeason']['subSeason']
                        player['current_season_stats'] = full_player_data['featuredStats']['regularSeason']['subSeason']
                
                enhanced_players.append(player)
        except:
            pass

players = enhanced_players
print(f"✅ Enhanced {len(players)} players with stats")

# Filter to specific teams
teams = ['WSH', 'NYI', 'ANA', 'DET']
filtered_goalies = [p for p in players if p.get('team') in teams and p.get('position') == 'G']

print(f"\n{'='*80}")
print(f"Total goalies in {', '.join(teams)}: {len(filtered_goalies)}")
print(f"{'='*80}\n")

# Load prices
prices = fetcher.parse_price_csv('hraci_ceny.csv')
players = fetcher.match_players_with_prices(players, prices, debug_output=False)

# Calculate fantasy points
scorer = FantasyScorer()
filtered_goalies_with_prices = [p for p in players if p.get('team') in teams and p.get('position') == 'G' and p.get('cena', 0) > 0]

print(f"Goalies with prices: {len(filtered_goalies_with_prices)}\n")

for goalie in filtered_goalies_with_prices:
    fantasy_points = scorer.calculate_points(goalie)
    value_score = goalie.get('cena', 0) / fantasy_points if fantasy_points > 0 else 0
    value_per_cost = fantasy_points / goalie.get('cena', 1) if goalie.get('cena', 0) > 0 else 0
    
    print(f"{goalie.get('name'):20s} ({goalie.get('team')}) - ${goalie.get('cena', 0):.1f}M")
    print(f"  Fantasy Points: {fantasy_points:.1f}")
    print(f"  Value Score: {value_score:.2f}")
    print(f"  Value per Cost: {value_per_cost:.2f}")
    
    # Check stats
    stats = goalie.get('stats', {})
    print(f"  Stats: GP={stats.get('gamesPlayed', 0)}, W={stats.get('wins', 0)}, L={stats.get('losses', 0)}")
    print()
