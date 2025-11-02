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
import requests

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
            failed_count = 0
            
            for i, player in enumerate(self.players):
                player_id = player.get('id')
                if player_id:
                    if i % 50 == 0:  # Less frequent updates
                        print(f"  Processing players {i+1}-{min(i+50, len(self.players))}/{len(self.players)}...")
                    
                    try:
                        # Fetch the full player data with stats structure
                        cache_file = os.path.join(self.fetcher.cache_dir, f"player_{player_id}.json")
                        full_player_data = None
                        
                        # Try to load from cache first
                        if os.path.exists(cache_file):
                            try:
                                with open(cache_file, 'r', encoding='utf-8') as f:
                                    full_player_data = json.load(f)
                            except:
                                pass
                        
                        # If not in cache, fetch it
                        if not full_player_data:
                            try:
                                url = f"{self.fetcher.base_url}/player/{player_id}/landing"
                                response = requests.get(url, timeout=10)
                                response.raise_for_status()
                                full_player_data = response.json()
                                # Cache it
                                with open(cache_file, 'w', encoding='utf-8') as f:
                                    json.dump(full_player_data, f, ensure_ascii=False, indent=2)
                            except Exception as e:
                                failed_count += 1
                                if failed_count < 5:
                                    print(f"  ⚠️  Could not fetch data for player {player_id}: {e}")
                                continue
                        
                        # Merge the full data structure into player object
                        # This preserves featuredStats, seasonTotals, etc.
                        if full_player_data:
                            # Keep existing player data but add the stats structures
                            if 'featuredStats' in full_player_data:
                                player['featuredStats'] = full_player_data['featuredStats']
                            if 'seasonTotals' in full_player_data:
                                player['seasonTotals'] = full_player_data['seasonTotals']
                            if 'careerTotals' in full_player_data:
                                player['careerTotals'] = full_player_data['careerTotals']
                            
                            # Also add legacy keys for compatibility
                            if 'featuredStats' in full_player_data and 'regularSeason' in full_player_data['featuredStats']:
                                if 'subSeason' in full_player_data['featuredStats']['regularSeason']:
                                    player['stats'] = full_player_data['featuredStats']['regularSeason']['subSeason']
                                    player['current_season_stats'] = full_player_data['featuredStats']['regularSeason']['subSeason']
                            
                            enhanced_players.append(player)
                        else:
                            # No stats available, skip this player
                            failed_count += 1
                    except Exception as e:
                        # Error fetching stats, skip this player
                        failed_count += 1
                        if failed_count < 5:  # Only show first few errors
                            print(f"  ⚠️  Could not fetch stats for player {player_id}: {e}")
                else:
                    # No player ID, skip
                    failed_count += 1
            
            self.players = enhanced_players
            print(f"✅ Enhanced {len(enhanced_players)} players with current season stats")
            if failed_count > 0:
                print(f"⚠️  Skipped {failed_count} players (no stats available)")

        else:
            print("❌ Invalid source or missing filepath")
            return False
        
        if not self.players:
            print("❌ No player data loaded")
            return False
        
        # Filter by teams if specified
        if teams:
            print(f"\n🔍 Filtering players to teams: {', '.join(teams)}")
            players_before = len(self.players)
            self.players = self.fetcher.filter_teams_by_gameday(self.players, teams)
            print(f"✅ Filtered from {players_before} to {len(self.players)} players")
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
        """
        print("\n🧮 Calculating fantasy points and player values...")
        
        # Remove duplicates
        unique_players = {}
        for player in self.players:
            name = player.get('name', '')
            if not name:
                continue
            
            if name not in unique_players:
                unique_players[name] = player
            else:
                existing = unique_players[name]
                existing_price = existing.get('cena', 0)
                new_price = player.get('cena', 0)
                
                if new_price > 0 and existing_price == 0:
                    unique_players[name] = player
        
        self.players = list(unique_players.values())
        print(f"✓ Removed duplicates, kept {len(self.players)} unique players")
        
        # Calculate base fantasy points
        players_with_points = 0
        players_without_stats = 0
        
        for player in self.players:
            if not player.get('position'):
                player['position'] = 'F'
            
            cost = player.get('cena', 0)
            
            if cost <= 0:
                player['fantasy_points'] = 0
                player['correlation_bonus'] = 0
                player['total_fantasy_points'] = 0
                player['value_score'] = 0
                player['projected_points'] = 0
                player['value_per_cost'] = 0
                continue
            
            # Check if player has stats
            if not self._has_required_stats(player):
                player['fantasy_points'] = 0
                player['correlation_bonus'] = 0
                player['total_fantasy_points'] = 0
                player['value_score'] = 0
                player['projected_points'] = 0
                player['value_per_cost'] = 0
                players_without_stats += 1
                continue
            
            # Calculate fantasy points
            fantasy_points = self.scorer.calculate_points(player)
            player['fantasy_points'] = fantasy_points
            
            if fantasy_points > 0:
                players_with_points += 1
        
        print(f"✓ Calculated points for {players_with_points} players")
        if players_without_stats > 0:
            print(f"⚠️  {players_without_stats} players have prices but no stats")
        
        # Group by position for correlation bonuses
        print("\n🔍 Analyzing top performers for correlation bonuses...")
        
        position_groups = {'G': [], 'D': [], 'F': []}
        for player in self.players:
            if player.get('fantasy_points', 0) > 0:
                pos = self.scorer._normalize_position(player.get('position', 'F'))
                position_groups[pos].append(player)
        
        top_performers = {}
        for pos, players_list in position_groups.items():
            sorted_players = sorted(players_list, key=lambda p: p.get('fantasy_points', 0), reverse=True)
            top_performers[pos] = sorted_players[:10]
            
            if sorted_players:
                print(f"  {pos}: Top = {sorted_players[0].get('name')} ({sorted_players[0].get('fantasy_points', 0):.1f} FP)")
        
        # Calculate correlation bonuses and final values
        total_fantasy_points = 0
        total_bonuses = 0
        zero_point_count = 0
        
        for player in self.players:
            cost = player.get('cena', 0)
            
            if cost <= 0:
                continue
            
            base_fp = player.get('fantasy_points', 0)
            
            if base_fp == 0:
                zero_point_count += 1
                player['correlation_bonus'] = 0
                player['total_fantasy_points'] = 0
                player['value_score'] = 0
                player['projected_points'] = 0
                player['value_per_cost'] = 0
                continue
            
            # Get correlation bonus
            pos = self.scorer._normalize_position(player.get('position', 'F'))
            top_in_position = top_performers.get(pos, [])
            
            bonus = self.scorer.calculate_correlation_bonus(player, top_in_position, pos)
            
            # Calculate totals
            total_fp = base_fp + bonus
            value_score = total_fp / cost
            
            player['correlation_bonus'] = bonus
            player['total_fantasy_points'] = total_fp
            player['value_score'] = value_score
            player['projected_points'] = total_fp
            player['value_per_cost'] = value_score
            
            total_fantasy_points += total_fp
            total_bonuses += bonus
        
        print(f"\n✅ Final results:")
        print(f"   Season weighting: DYNAMIC sigmoid curve based on games played")
        print(f"     • Very early (0 games): 15% current, 85% previous")
        print(f"     • Early season (10 games): ~25% current, 75% previous")
        print(f"     • Mid season (35 games): ~50% current, 50% previous")
        print(f"     • Late season (60 games): ~80% current, 20% previous")
        print(f"     • Very late (82 games): ~92% current, 8% previous")
        print(f"   Rookie amplification: DYNAMIC exponential decay")
        print(f"     • 1-10 games: 1.35x-1.25x boost (small sample uncertainty)")
        print(f"     • 10-40 games: 1.25x-1.10x boost (establishing baseline)")
        print(f"     • 40-82 games: 1.10x-1.05x boost (large sample confidence)")
        print(f"   Players with points > 0: {players_with_points}")
        print(f"   Players with 0 points: {zero_point_count}")
        print(f"   Total fantasy points: {total_fantasy_points:.1f}")
        print(f"   Total bonuses: {total_bonuses:.1f}")
        
        # Show detailed scoring breakdown for sample players from each position
        print("\n" + "=" * 70)
        print("DETAILED SCORING EXAMPLES")
        print("=" * 70)
        
        for pos in ['F', 'D', 'G']:
            pos_players = [p for p in self.players 
                          if self.scorer._normalize_position(p.get('position', '')) == pos 
                          and p.get('fantasy_points', 0) > 0]
            
            if pos_players:
                # Show breakdown for the highest scoring player in this position
                top_player = max(pos_players, key=lambda p: p.get('fantasy_points', 0))
                breakdown = self.scorer.generate_scoring_breakdown(top_player)
                print("\n" + breakdown)
        
        print("\n" + "=" * 70)
        
        # Show top 5 value players
        top_players = sorted(
            [p for p in self.players if p.get('value_score', 0) > 0],
            key=lambda p: p.get('value_score', 0),
            reverse=True
        )[:5]
        
        if top_players:
            print("\n🏆 Top 5 Players by Value:")
            for i, p in enumerate(top_players, 1):
                stats = self.scorer._extract_combined_stats(p)
                goals = self.scorer._get_stat(stats, 'goals', 'g')
                assists = self.scorer._get_stat(stats, 'assists', 'a')
                games = self.scorer._get_stat(stats, 'gamesPlayed', 'games', 'gp')
                
                print(f"  {i}. {p.get('name')} ({p.get('position')})")
                print(f"      ${p.get('cena'):.1f}M | {int(games)}GP | {int(goals)}G {int(assists)}A")
                print(f"      FP: {p.get('fantasy_points'):.1f} + Bonus: {p.get('correlation_bonus'):.1f}")
                print(f"      Total: {p.get('total_fantasy_points'):.1f} | Value: {p.get('value_score'):.2f}")

    def _has_required_stats(self, player: Dict) -> bool:
        """
        Checks if player has the minimum required statistics for scoring.
        
        Args:
            player: Player dictionary
            
        Returns:
            True if player has required stats, False otherwise
        """
        # For API data, check if 'stats' is present
        if 'stats' in player and isinstance(player['stats'], dict):
            return True
            
        # Check for current_season_stats
        if 'current_season_stats' in player and isinstance(player['current_season_stats'], dict):
            return True
            
        # Check for basic flat stats
        basic_stats = ['goals', 'assists', 'shots', 'hits', 'blocked_shots']
        has_stats = any(stat in player for stat in basic_stats)
        
        return has_stats

    def optimize_lineup(
        self,
        method: str = 'greedy',
        budget: Optional[float] = None,
        use_advanced: bool = False
    ) -> tuple:
        """
        Generates the optimal fantasy lineup based on calculated player values.
        
        Args:
            method: 'greedy' for fast, 'iterative' for better, 'advanced' for ML-based
            budget: Custom budget limit (uses default if None)
            use_advanced: Whether to use advanced GameScore-based optimization
            
        Returns:
            Tuple of (lineup, total_cost, effective_points)
        """
        if use_advanced or method == 'advanced':
            print(f"\n🎯 Using advanced ML-based optimization...")
            from advanced_optimizer import AdvancedLineupOptimizer
            
            adv_optimizer = AdvancedLineupOptimizer(
                base_budget=budget or 100.0,
                max_budget=(budget or 100.0) * 1.2
            )
            
            lineup, cost, points, df = adv_optimizer.optimize_lineup(self.players)
            
            # Save DataFrame for analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            df.to_csv(f"optimization_data_{timestamp}.csv", index=False)
            print(f"💾 Saved optimization data to optimization_data_{timestamp}.csv")
            
            return lineup, cost, points
        
        print(f"\n🎯 Optimizing lineup using {method} method...")
        print(f"   Base budget: ${self.optimizer.constraints.base_budget:.1f}M (no penalty)")
        print(f"   Penalty: {self.optimizer.constraints.penalty_per_million*100:.1f}% per $1M over base")
        if budget:
            print(f"   Custom target budget: ${budget:.1f}M")
        
        if method == 'iterative':
            lineup, cost, points = self.optimizer.optimize_lineup_iterative(
                self.players,
                iterations=1000
            )
        else:  # greedy
            lineup, cost, points = self.optimizer.build_greedy_lineup(
                self.players,
                max_budget=budget
            )
        
        print(f"✅ Optimization complete!")
        return lineup, cost, points
    
    def cleanup_old_reports(self, output_dir: str = '.') -> None:
        """
        Remove old report files before generating new ones.
        Keeps lineup_history.json for comparison feature.
        
        Args:
            output_dir: Directory containing output files
        """
        import glob
        
        patterns = [
            'optimal_lineup_*.txt',
            'player_rankings_*.csv',
            'player_rankings_*.md',
            'player_rankings_*.txt',
            'players_with_scores_*.json'
        ]
        
        removed_count = 0
        for pattern in patterns:
            full_pattern = os.path.join(output_dir, pattern)
            for filepath in glob.glob(full_pattern):
                try:
                    os.remove(filepath)
                    removed_count += 1
                except Exception as e:
                    print(f"⚠️  Could not remove {filepath}: {e}")
        
        if removed_count > 0:
            print(f"🧹 Cleaned up {removed_count} old report file(s)")
    
    def generate_reports(
        self,
        lineup: List[Dict],
        cost: float,
        points: float,
        output_dir: str = '.'
    ) -> None:
        """
        Generates and saves various reports and rankings.
        
        Args:
            lineup: Optimized player lineup
            cost: Total lineup cost
            points: Effective fantasy points
            output_dir: Directory to save output files
        """
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Clean up old report files
        self.cleanup_old_reports(output_dir)
        
        print("\n📝 Generating reports...")
        
        # Generate lineup report
        lineup_report = self.optimizer.generate_lineup_report(lineup, cost, points)
        print(lineup_report)
        
        # Save lineup report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        lineup_filename = os.path.join(output_dir, f"optimal_lineup_{timestamp}.txt")
        
        try:
            with open(lineup_filename, 'w', encoding='utf-8') as f:
                f.write(lineup_report)
            print(f"\n💾 Lineup saved to: {lineup_filename}")
        except Exception as e:
            print(f"⚠️  Could not save lineup file: {e}")
        
        # Generate player rankings
        rankings_text = self.optimizer.export_rankings(self.players, 'text')
        rankings_csv = self.optimizer.export_rankings(self.players, 'csv')
        rankings_md = self.optimizer.export_rankings(self.players, 'markdown')
        
        # Save rankings in multiple formats
        try:
            with open(os.path.join(output_dir, f"player_rankings_{timestamp}.txt"), 'w', encoding='utf-8') as f:
                f.write(rankings_text)
            with open(os.path.join(output_dir, f"player_rankings_{timestamp}.csv"), 'w', encoding='utf-8') as f:
                f.write(rankings_csv)
            with open(os.path.join(output_dir, f"player_rankings_{timestamp}.md"), 'w', encoding='utf-8') as f:
                f.write(rankings_md)
            print(f"💾 Rankings saved in multiple formats")
        except Exception as e:
            print(f"⚠️  Could not save ranking files: {e}")
        
        # Save processed player data with all calculated values
        self.fetcher.save_to_json(
            self.players,
            os.path.join(output_dir, f"players_with_scores_{timestamp}.json")
        )
    
    def run_full_analysis(
        self,
        data_source: str,
        filepath: Optional[str] = None,
        price_file: Optional[str] = None,
        method: str = 'greedy',
        output_dir: str = '.',
        teams: Optional[List[str]] = None,
        gameday: Optional[str] = None,
        use_advanced: bool = False
    ) -> bool:
        """
        Runs the complete analysis workflow from data loading to report generation.
        
        Args:
            data_source: 'csv', 'json', or 'api'
            filepath: Path to input file
            price_file: Path to text file with player prices
            method: Optimization method to use
            output_dir: Where to save output files
            teams: Optional list of team abbreviations to filter by
            gameday: Optional date string to filter by gameday
            use_advanced: Whether to use advanced ML-based optimization
            
        Returns:
            True if successful, False otherwise
        """
        print("=" * 70)
        print("NHL FANTASY LINEUP OPTIMIZER")
        print("=" * 70)
        
        # Step 1: Load data with team/gameday filtering
        if not self.load_data(data_source, filepath, price_file, teams, gameday):
            return False
        
        # Step 2: Calculate scores
        self.calculate_all_scores()
        
        # Debug output
        print("\n🔍 Debug Information:")
        priced_players = [p for p in self.players if p.get('cena', 0) > 0]
        valid_players = [p for p in priced_players if p.get('projected_points', 0) > 0]
        
        print(f"  Total players loaded: {len(self.players)}")
        print(f"  Players with prices: {len(priced_players)}")
        print(f"  Players with both prices & points: {len(valid_players)}")
        
        if not valid_players:
            print("❌ Error: No players with both valid prices and points!")
            print("Check that player prices were loaded correctly and points were calculated.")
            return False
            
        if len(valid_players) < 12:  # Minimum for a complete lineup
            print(f"⚠️  Warning: Only {len(valid_players)} valid players - may not form complete lineup!")
        
        # Step 3: Optimize lineup
        lineup, cost, points = self.optimize_lineup(method, use_advanced=use_advanced)
        
        if not lineup:
            print("❌ No valid lineup could be created")
            return False
            
        # Step 4: Generate reports and save history
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._save_history(lineup, cost, points, timestamp)
        self.generate_reports(lineup, cost, points, output_dir)
        
        # Step 5: Show comparison with previous lineup if available
        if len(self.history) > 1:
            self._show_lineup_comparison()
        
        print("\n✅ Analysis complete!")
        print("=" * 70)
        return True
        
    def _show_lineup_comparison(self) -> None:
        """Shows comparison between current and previous lineup"""
        if len(self.history) < 2:
            return
            
        current = self.history[-1]
        previous = self.history[-2]
        
        print("\n📊 Lineup Comparison (Current vs Previous):")
        print(f"  Date: {current['timestamp']} vs {previous['timestamp']}")
        print(f"  Cost: ${current['cost']:.2f}M vs ${previous['cost']:.2f}M ({current['cost'] - previous['cost']:.2f}M)")
        print(f"  Points: {current['points']:.2f} vs {previous['points']:.2f} ({current['points'] - previous['points']:.2f})")
        
        # Players in both lineups
        current_players = {p['name'] for p in current['lineup']}
        previous_players = {p['name'] for p in previous['lineup']}
        common_players = current_players.intersection(previous_players)
        
        print(f"  Changed players: {len(current_players) - len(common_players)}/{len(current_players)}")
        
        # New additions worth mentioning
        if len(current_players - previous_players) > 0:
            print("  Notable additions:")
            for player in current['lineup']:
                if player['name'] in current_players - previous_players:
                    print(f"    + {player['name']} ({player['position']}) - {player['points']:.1f} pts")


def main():
    """
    Command-line interface for the NHL Fantasy Optimizer.
    """
    parser = argparse.ArgumentParser(
        description='NHL Fantasy Lineup Optimizer - Build the best fantasy team!',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic greedy optimization
  python main.py --source api --prices hraci_ceny.csv
  
  # Advanced ML-based optimization with GameScore
  python main.py --source api --prices hraci_ceny.csv --method advanced
        """
    )
    
    parser.add_argument(
        '--source',
        type=str,
        choices=['csv', 'json', 'api', 'tipsport'],
        help='Data source type'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Path to input file (required for csv/json/tipsport sources)'
    )
    
    parser.add_argument(
        '--prices',
        type=str,
        help='Path to CSV/text file containing player prices (hraci_ceny.csv format)'
    )
    
    parser.add_argument(
        '--method',
        type=str,
        choices=['greedy', 'iterative', 'advanced'],
        default='greedy',
        help='Optimization method (default: greedy)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='.',
        help='Output directory for reports (default: current directory)'
    )
    
    parser.add_argument(
        '--budget',
        type=float,
        default=100.0,
        help='Custom budget limit in millions (default: 100.0)'
    )
    
    parser.add_argument(
        '--refresh',
        action='store_true',
        help='Force refresh all cached data'
    )
    
    parser.add_argument(
        '--no-interactive',
        action='store_true',
        help='Disable interactive prompts'
    )
    
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear all cached data and exit'
    )
    
    parser.add_argument(
        '--history',
        action='store_true',
        help='Show lineup history and exit'
    )
    
    parser.add_argument(
        '--teams',
        type=str,
        help='Comma-separated list of team abbreviations to filter by (e.g. TOR,BOS,MTL)'
    )
    
    parser.add_argument(
        '--gameday',
        type=str,
        help='Filter by teams playing on a specific date (format: YYYY-MM-DD or "today")'
    )
    
    parser.add_argument(
        '--advanced',
        action='store_true',
        help='Use advanced ML-based optimization (same as --method advanced)'
    )
    
    args = parser.parse_args()
    
    # Process team list if provided
    teams = None
    if args.teams:
        teams = [t.strip() for t in args.teams.split(',')]
        
    # Process gameday
    gameday = None
    if args.gameday:
        if args.gameday.lower() == 'today':
            from datetime import datetime
            gameday = datetime.now().strftime('%Y-%m-%d')
        else:
            gameday = args.gameday
    
    # Create app instance for history or cache operations
    app = NHLFantasyApp(force_refresh=args.refresh, interactive=not args.no_interactive)
    
    # Handle cache clearing
    if args.clear_cache:
        fetcher = NHLDataFetcher()
        fetcher.clear_cache()
        return 0
        
    # Show history if requested
    if args.history:
        if app.history:
            print("\n📜 Lineup History:")
            for i, entry in enumerate(app.history):
                print(f"\n{i+1}. {entry['timestamp']} - ${entry['cost']:.2f}M, {entry['points']:.2f} pts")
                print("   Players:")
                for p in entry['lineup']:
                    print(f"   - {p['name']} ({p['position']}) - {p['points']:.1f} pts")
        else:
            print("No lineup history found")
        return 0
    
    # Validate required arguments
    if not args.source:
        parser.error("--source is required (use --clear-cache or --history to only perform those operations)")
    
    # Validate file argument for csv/json/tipsport
    if args.source in ['csv', 'json', 'tipsport'] and not args.file:
        parser.error(f"--file is required when using --source {args.source}")
    
    # If custom budget specified, update optimizer constraints
    if args.budget:
        app.optimizer.constraints.base_budget = args.budget
        app.optimizer.constraints.max_budget = args.budget * 2

    # Determine if advanced mode should be used (either --advanced flag or --method advanced)
    use_advanced_mode = args.advanced or (args.method == 'advanced')

    # Run the full analysis
    try:
        success = app.run_full_analysis(
            data_source=args.source,
            filepath=args.file,
            price_file=args.prices,
            method=args.method if args.method != 'advanced' else 'greedy',
            output_dir=args.output,
            teams=teams,
            gameday=gameday,
            use_advanced=use_advanced_mode
        )
        return 0 if success else 1
    except Exception as e:
        print(f"Fatal error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1


# Ensure the process exits with main()'s return code
if __name__ == "__main__":
    sys.exit(main())
