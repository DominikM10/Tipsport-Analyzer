"""
NHL Fantasy Optimization - Main Application
Entry point that orchestrates data fetching, scoring, and lineup optimization.
Provides command-line interface for easy usage.
"""

import argparse
import sys
import os
import time
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import json

# Import our custom modules
from data_fetch import NHLDataFetcher
from scoring import FantasyScorer
from optimizer import LineupOptimizer, LineupConstraints


class NHLFantasyApp:
    """
    Main application class that coordinates all components of the fantasy optimizer.
    Handles the full workflow from data input to lineup generation.
    """
    
    def __init__(self, force_refresh=False, interactive=True):
        self.interactive = interactive
        self.force_refresh = force_refresh
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lineup_history.json')
        self.history = self._load_history()
        
        # Check if we should clear cache before initializing
        if self.interactive and not force_refresh:
            self._check_cache_status()
        
        self.fetcher = NHLDataFetcher(force_refresh=force_refresh)
        self.scorer = FantasyScorer()
        self.optimizer = LineupOptimizer()
        self.players = []
    
    def _load_history(self) -> List[Dict]:
        """Loads lineup history from JSON file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load history: {e}")
        return []
        
    def _save_history(self, lineup: List[Dict], cost: float, points: float, timestamp: str) -> None:
        """Saves lineup to history file"""
        history_entry = {
            'timestamp': timestamp,
            'cost': cost,
            'points': points,
            'lineup': [
                {
                    'name': p.get('name', 'Unknown'),
                    'position': p.get('position', '?'),
                    'team': p.get('team', '?'),
                    'cost': p.get('cena', 0),
                    'points': p.get('projected_points', 0)
                } for p in lineup
            ]
        }
        
        # Add to history
        self.history.append(history_entry)
        
        # Keep only last 10 lineups
        if len(self.history) > 10:
            self.history = self.history[-10:]
            
        # Save to file
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save history: {e}")

    def _check_cache_status(self):
        """
        Checks cache status and prompts user whether to refresh.
        Handles errors gracefully.
        """
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
        
        if os.path.exists(cache_dir):
            # Check cache age
            try:
                cache_files = list(Path(cache_dir).glob('*'))
                if cache_files:
                    newest_file = max(cache_files, key=lambda p: p.stat().st_mtime)
                    age_hours = (time.time() - newest_file.stat().st_mtime) / 3600
                    
                    print(f"\n📁 Cache Status:")
                    print(f"   Location: {cache_dir}")
                    print(f"   Files: {len(cache_files)}")
                    print(f"   Age: {age_hours:.1f} hours")
                    print()
                    
                    response = input("Clear cache and fetch fresh data? (y/N): ").strip().lower()
                    if response in ['y', 'yes']:
                        self.force_refresh = True
                        try:
                            fetcher = NHLDataFetcher()
                            fetcher.clear_cache()
                        except Exception as e:
                            print(f"Warning: Could not fully clear cache: {e}")
                            print("Continuing with partial cache...")
                        print()
            except Exception as e:
                print(f"Warning: Could not check cache status: {e}")
                print("Continuing without cache verification...")

    def load_data(
        self,
        source: str,
        filepath: Optional[str] = None,
        price_file: Optional[str] = None,
        teams: Optional[List[str]] = None,
        gameday: Optional[str] = None
    ) -> bool:
        """
        Loads player data from specified source.
        
        Args:
            source: 'api', 'csv', 'json', or 'tipsport'
            filepath: Path to file if using csv/json/tipsport
            price_file: Optional path to CSV file with player prices (hraci_ceny.csv format)
            teams: Optional list of team abbreviations to filter by
            gameday: Optional date (YYYY-MM-DD) to get teams playing on that day
            
        Returns:
            True if successful, False otherwise
        """
        print(f"\n📊 Loading data from {source}...")
        
        # Get teams playing on specified gameday
        if gameday:
            print(f"📆 Looking up teams playing on {gameday}...")
            schedule = self.fetcher.get_team_schedule(gameday)
            gameday_teams = schedule.get(gameday, [])
            
            if gameday_teams:
                print(f"Found {len(gameday_teams)} teams playing on {gameday}: {', '.join(gameday_teams)}")
                # If user provided teams AND gameday, take intersection
                if teams:
                    teams = [t for t in teams if t.upper() in [gt.upper() for gt in gameday_teams]]
                    print(f"Filtering to {len(teams)} teams from both user selection and game day")
                else:
                    teams = gameday_teams
            else:
                print(f"No games found for {gameday}")
        
        # Load player data from selected source
        if source == 'csv' and filepath:
            self.players = self.fetcher.load_from_csv(filepath)
        elif source == 'json' and filepath:
            self.players = self.fetcher.load_from_json(filepath)
        elif source == 'tipsport' and filepath:
            # Use specialized Tipsport parser
            print("🔄 Parsing Tipsport fantasy hockey format...")
            self.players = self.fetcher.parse_tipsport_format(filepath)
            
            # Players already have prices from the parse
            if self.players:
                print(f"✅ Loaded {len(self.players)} players with prices from Tipsport")
        elif source == 'api':
            print("🔄 Fetching current player data from NHL API...")
            self.players = self.fetcher.fetch_all_players()
            
            # Enhance players with detailed stats
            print("🔄 Fetching detailed stats for players...")
            enhanced_players = []
            for i, player in enumerate(self.players):
                player_id = player.get('id')
                if player_id:
                    if i % 10 == 0:
                        print(f"  Processing player {i+1}/{len(self.players)}...")
                    
                    detailed_stats = self.fetcher.fetch_player_stats(player_id)
                    
                    player_copy = player.copy()
                    player_copy['stats'] = detailed_stats
                    player_copy['current_season_stats'] = detailed_stats.get('current_season', {})
                    player_copy['previous_season_stats'] = detailed_stats.get('previous_season', {})
                    
                    enhanced_players.append(player_copy)
                else:
                    enhanced_players.append(player)
                    
            self.players = enhanced_players
            print(f"✅ Enhanced {len(enhanced_players)} players with detailed stats")
        else:
            print("❌ Invalid source or missing filepath")
            return False
        
        if not self.players:
            print("❌ No player data loaded")
            return False
        
        # Filter by teams if specified
        if teams:
            self.players = self.fetcher.filter_teams_by_gameday(self.players, teams)
            if not self.players:
                print("❌ No players found after team filtering")
                return False
        
        # Apply player prices from CSV file
        players_with_prices = 0
        max_attempts = 3  # Allow multiple attempts to load prices
        
        for attempt in range(max_attempts):
            price_path = None
            
            # First attempt: use provided price file
            if attempt == 0 and price_file:
                price_path = price_file
                print(f"\n💲 Attempt {attempt + 1}: Loading player prices from: {price_path}")
            # Second attempt: look for default hraci_ceny.csv in current directory
            elif attempt == 1:
                # Check both CWD and script directory
                cwd_default = os.path.join(os.getcwd(), 'hraci_ceny.csv')
                script_dir_default = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hraci_ceny.csv')
                
                if os.path.exists(cwd_default):
                    price_path = cwd_default
                    print(f"\n💲 Attempt {attempt + 1}: Found default price file in working directory")
                    print(f"   Path: {price_path}")
                elif os.path.exists(script_dir_default):
                    price_path = script_dir_default
                    print(f"\n💲 Attempt {attempt + 1}: Found default price file in script directory")
                    print(f"   Path: {price_path}")
                else:
                    print(f"\n💲 Attempt {attempt + 1}: No default hraci_ceny.csv found")
                    price_path = None
            # Last attempt: prompt user to provide path if interactive mode is on
            elif self.interactive:
                print("\n" + "="*70)
                print("❌ No valid price file found. Players need prices to create a lineup.")
                print("="*70)
                print("\nThe price file should be a CSV with format:")
                print("  PlayerName,Whole,Decimal")
                print("  Example: Makar C.,30,9")
                print("\nOr with single price column:")
                print("  PlayerName,Price")
                print("  Example: Makar C.,30.9")
                print("\nCommon locations:")
                print(f"  1. Current directory: {os.path.join(os.getcwd(), 'hraci_ceny.csv')}")
                print(f"  2. Script directory: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hraci_ceny.csv')}")
                print(f"  3. Desktop: {os.path.join(os.path.expanduser('~'), 'Desktop', 'hraci_ceny.csv')}")
                print()
                
                price_path = input("Enter the full path to your price file (or 'q' to quit): ").strip()
                
                if price_path.lower() == 'q':
                    print("Exiting...")
                    return False
                    
                # Remove quotes if user copied path with them
                price_path = price_path.strip('"').strip("'")
                
                if not price_path or not os.path.exists(price_path):
                    print(f"❌ Invalid file path or file does not exist: {price_path}")
                    continue
                    
                print(f"\n💲 Attempt {attempt + 1}: Using user-provided path")
                print(f"   Path: {price_path}")
            else:
                # Skip if not interactive and no valid price file
                print(f"\n💲 Attempt {attempt + 1}: Skipped (non-interactive mode)")
                price_path = None

            if not price_path:
                # Try next attempt
                continue

            # Verify file exists before attempting to parse
            if not os.path.exists(price_path):
                print(f"❌ File does not exist: {price_path}")
                continue

            print(f"✓ File found: {price_path}")
            print(f"✓ File size: {os.path.getsize(price_path)} bytes")

            # Try to parse the price file
            prices = {}
            try:
                if price_path.lower().endswith('.csv'):
                    print("✓ Parsing as CSV format...")
                    prices = self.fetcher.parse_price_csv(price_path, debug=True)
                else:
                    print("✓ Parsing as text format...")
                    prices = self.fetcher.parse_player_prices_from_text(price_path)
            except Exception as e:
                print(f"❌ Error parsing price file: {e}")
                import traceback
                traceback.print_exc()
                continue

            if prices:
                print(f"✅ Successfully parsed {len(prices)} price entries from file")
                
                # Show sample of parsed prices
                print("\nSample of parsed prices:")
                for i, (name, price) in enumerate(list(prices.items())[:5]):
                    print(f"  {i+1}. {name} = ${price}M")
                
                # Match players with prices
                print(f"\n🔄 Matching {len(self.players)} players with {len(prices)} prices...")
                self.players = self.fetcher.match_players_with_prices(self.players, prices)
                
                players_with_prices = sum(1 for p in self.players if p.get('cena', 0) > 0)
                print(f"✅ Successfully matched {players_with_prices} players with prices")

                # Show sample of matched players
                if players_with_prices > 0:
                    print("\nSample of matched players:")
                    matched_samples = [p for p in self.players if p.get('cena', 0) > 0][:5]
                    for i, p in enumerate(matched_samples, 1):
                        print(f"  {i}. {p.get('name')} ({p.get('position', '?')}) = ${p.get('cena')}M")

                # Break the loop if we've successfully applied prices to some players
                if players_with_prices > 0:
                    break
                else:
                    print("⚠️  No players were matched with prices. Check player_price_matching.json for details.")
            else:
                print("⚠️ Could not parse any prices from the file")
        
        # Final summary
        print(f"\n{'='*70}")
        print(f"DATA LOADING SUMMARY")
        print(f"{'='*70}")
        print(f"Total players loaded: {len(self.players)}")
        print(f"Players with prices: {players_with_prices}")
        print(f"Coverage: {(players_with_prices/len(self.players)*100):.1f}%" if self.players else "0%")
        print(f"{'='*70}\n")
        
        return True
    
    def calculate_all_scores(
        self,
        weight_current: float = 1.0,
        weight_previous: float = 0.0,
        weight_advanced: float = 0.0
    ) -> None:
        """
        Calculates fantasy points and value scores for all loaded players.
        
        Process:
        1. Remove duplicates
        2. For each player with price and stats:
           a. Calculate fantasy points from their statistics
           b. Calculate value = fantasy_points / price
        """
        print("\n🧮 Calculating fantasy points and player values...")
        
        # FIRST: Remove duplicate players (keep one with best stats or price)
        unique_players = {}
        for player in self.players:
            name = player.get('name', '')
            if not name:
                continue
            
            # If we haven't seen this player, add them
            if name not in unique_players:
                unique_players[name] = player
            else:
                # Keep the one with a price, or better stats
                existing = unique_players[name]
                existing_price = existing.get('cena', 0)
                new_price = player.get('cena', 0)
                
                # Prefer player with price
                if new_price > 0 and existing_price == 0:
                    unique_players[name] = player
                elif existing_price > 0 and new_price == 0:
                    pass  # Keep existing
                else:
                    # Both have prices or both don't - keep first
                    pass
        
        self.players = list(unique_players.values())
        print(f"✓ Removed duplicates, kept {len(self.players)} unique players")
        
        scored_count = 0
        skipped_no_price = 0
        skipped_no_stats = 0
        total_fantasy_points = 0
        
        for player in self.players:
            # Ensure position is set
            if not player.get('position'):
                player['position'] = 'F'
            
            # Must have price to be in lineup
            cost = player.get('cena', 0)
            if cost <= 0:
                player['fantasy_points'] = 0
                player['value_score'] = 0
                player['projected_points'] = 0
                player['value_per_cost'] = 0
                skipped_no_price += 1
                continue
            
            # Check if player has necessary stats
            if not self._has_required_stats(player):
                player['fantasy_points'] = 0
                player['value_score'] = 0
                player['projected_points'] = 0
                player['value_per_cost'] = 0
                skipped_no_stats += 1
                continue
            
            # STEP 1: Calculate fantasy points from statistics
            fantasy_points = self.scorer.calculate_points(player)
            
            # STEP 2: Calculate value score (fantasy_points / price)
            value_score = fantasy_points / cost if cost > 0 else 0
            
            # Store all calculated values
            player['fantasy_points'] = fantasy_points
            player['value_score'] = value_score
            player['projected_points'] = fantasy_points  # Use actual fantasy points
            player['value_per_cost'] = value_score
            
            scored_count += 1
            total_fantasy_points += fantasy_points
        
        print(f"✅ Calculated fantasy points for {scored_count} players")
        print(f"   Total fantasy points across all players: {total_fantasy_points:.1f}")
        print(f"⚠️  Skipped {skipped_no_price} players without prices")
        print(f"⚠️  Skipped {skipped_no_stats} players without stats")
