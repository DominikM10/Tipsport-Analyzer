"""
NHL Data Fetching Module
This module handles retrieving player statistics from the NHL API or local files.
It supports both current season and historical data for comprehensive analysis.
"""

import requests
import json
import csv
import os
import re
import time
import shutil
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import difflib
from pathlib import Path
import unicodedata


class NHLDataFetcher:
    """
    Fetches NHL player statistics from the official NHL API or local files.
    Supports multiple data sources and formats for flexibility.
    """
    
    def __init__(self, force_refresh=False, cache_dir=None):
        # Base URL for the official NHL Stats API
        self.base_url = "https://api-web.nhle.com/v1"
        self.current_season = self._get_current_season()
        self.previous_season = self._get_previous_season()
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
        self.force_refresh = force_refresh
        self._ensure_cache_dir()
        
    def _ensure_cache_dir(self):
        """Creates cache directory if it doesn't exist."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def _cache_is_valid(self, cache_file, max_age_hours=12):
        """Check if cached data is still valid based on file modification time."""
        if not os.path.exists(cache_file):
            return False
            
        if self.force_refresh:
            return False
            
        mod_time = os.path.getmtime(cache_file)
        current_time = time.time()
        age_hours = (current_time - mod_time) / 3600
        
        return age_hours < max_age_hours
        
    def _get_current_season(self) -> str:
        """
        Determines the current NHL season based on today's date.
        NHL seasons span two calendar years (e.g., 20242025).
        """
        now = datetime.now()
        # NHL season runs October through June
        if now.month < 7:  # Before July, use previous year's season
            return f"{now.year - 1}{now.year}"
        else:  # July or later, use upcoming season
            return f"{now.year}{now.year + 1}"
    
    def _get_previous_season(self) -> str:
        """
        Returns the season before the current one.
        """
        current = self._get_current_season()
        start_year = int(current[:4])
        return f"{start_year - 1}{start_year}"
    
    def fetch_all_teams(self) -> List[Dict]:
        """
        Fetches list of all NHL teams.
        
        Returns:
            List of team dictionaries with basic info
        """
        cache_file = os.path.join(self.cache_dir, "all_teams.json")
        
        if self._cache_is_valid(cache_file, max_age_hours=168):  # Cache for 1 week
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        try:
            # NHL teams endpoint - using standings to get current teams
            url = f"{self.base_url}/standings/now"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            standings_data = response.json()
            
            teams = []
            seen_teams = set()
            
            # Extract teams from standings
            for standing in standings_data.get('standings', []):
                team_abbrev = standing.get('teamAbbrev', {}).get('default', '')
                team_name = standing.get('teamName', {}).get('default', '')
                
                if team_abbrev and team_abbrev not in seen_teams:
                    teams.append({
                        'abbrev': team_abbrev,
                        'name': team_name,
                        'id': standing.get('teamId')
                    })
                    seen_teams.add(team_abbrev)
            
            # If standings didn't work, use hardcoded list of current NHL teams
            if not teams:
                teams = [
                    {'abbrev': 'ANA', 'name': 'Anaheim Ducks'},
                    {'abbrev': 'BOS', 'name': 'Boston Bruins'},
                    {'abbrev': 'BUF', 'name': 'Buffalo Sabres'},
                    {'abbrev': 'CAR', 'name': 'Carolina Hurricanes'},
                    {'abbrev': 'CBJ', 'name': 'Columbus Blue Jackets'},
                    {'abbrev': 'CGY', 'name': 'Calgary Flames'},
                    {'abbrev': 'CHI', 'name': 'Chicago Blackhawks'},
                    {'abbrev': 'COL', 'name': 'Colorado Avalanche'},
                    {'abbrev': 'DAL', 'name': 'Dallas Stars'},
                    {'abbrev': 'DET', 'name': 'Detroit Red Wings'},
                    {'abbrev': 'EDM', 'name': 'Edmonton Oilers'},
                    {'abbrev': 'FLA', 'name': 'Florida Panthers'},
                    {'abbrev': 'LAK', 'name': 'Los Angeles Kings'},
                    {'abbrev': 'MIN', 'name': 'Minnesota Wild'},
                    {'abbrev': 'MTL', 'name': 'Montreal Canadiens'},
                    {'abbrev': 'NJD', 'name': 'New Jersey Devils'},
                    {'abbrev': 'NSH', 'name': 'Nashville Predators'},
                    {'abbrev': 'NYI', 'name': 'New York Islanders'},
                    {'abbrev': 'NYR', 'name': 'New York Rangers'},
                    {'abbrev': 'OTT', 'name': 'Ottawa Senators'},
                    {'abbrev': 'PHI', 'name': 'Philadelphia Flyers'},
                    {'abbrev': 'PIT', 'name': 'Pittsburgh Penguins'},
                    {'abbrev': 'SEA', 'name': 'Seattle Kraken'},
                    {'abbrev': 'SJS', 'name': 'San Jose Sharks'},
                    {'abbrev': 'STL', 'name': 'St. Louis Blues'},
                    {'abbrev': 'TBL', 'name': 'Tampa Bay Lightning'},
                    {'abbrev': 'TOR', 'name': 'Toronto Maple Leafs'},
                    {'abbrev': 'UTA', 'name': 'Utah Hockey Club'},
                    {'abbrev': 'VAN', 'name': 'Vancouver Canucks'},
                    {'abbrev': 'VGK', 'name': 'Vegas Golden Knights'},
                    {'abbrev': 'WPG', 'name': 'Winnipeg Jets'},
                    {'abbrev': 'WSH', 'name': 'Washington Capitals'}
                ]
            
            # Save to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(teams, f, ensure_ascii=False, indent=2)
            
            return teams
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching teams: {e}")
            # Return hardcoded list as fallback
            return [
                {'abbrev': 'ANA', 'name': 'Anaheim Ducks'},
                {'abbrev': 'BOS', 'name': 'Boston Bruins'},
                {'abbrev': 'BUF', 'name': 'Buffalo Sabres'},
                {'abbrev': 'CAR', 'name': 'Carolina Hurricanes'},
                {'abbrev': 'CBJ', 'name': 'Columbus Blue Jackets'},
                {'abbrev': 'CGY', 'name': 'Calgary Flames'},
                {'abbrev': 'CHI', 'name': 'Chicago Blackhawks'},
                {'abbrev': 'COL', 'name': 'Colorado Avalanche'},
                {'abbrev': 'DAL', 'name': 'Dallas Stars'},
                {'abbrev': 'DET', 'name': 'Detroit Red Wings'},
                {'abbrev': 'EDM', 'name': 'Edmonton Oilers'},
                {'abbrev': 'FLA', 'name': 'Florida Panthers'},
                {'abbrev': 'LAK', 'name': 'Los Angeles Kings'},
                {'abbrev': 'MIN', 'name': 'Minnesota Wild'},
                {'abbrev': 'MTL', 'name': 'Montreal Canadiens'},
                {'abbrev': 'NJD', 'name': 'New Jersey Devils'},
                {'abbrev': 'NSH', 'name': 'Nashville Predators'},
                {'abbrev': 'NYI', 'name': 'New York Islanders'},
                {'abbrev': 'NYR', 'name': 'New York Rangers'},
                {'abbrev': 'OTT', 'name': 'Ottawa Senators'},
                {'abbrev': 'PHI', 'name': 'Philadelphia Flyers'},
                {'abbrev': 'PIT', 'name': 'Pittsburgh Penguins'},
                {'abbrev': 'SEA', 'name': 'Seattle Kraken'},
                {'abbrev': 'SJS', 'name': 'San Jose Sharks'},
                {'abbrev': 'STL', 'name': 'St. Louis Blues'},
                {'abbrev': 'TBL', 'name': 'Tampa Bay Lightning'},
                {'abbrev': 'TOR', 'name': 'Toronto Maple Leafs'},
                {'abbrev': 'UTA', 'name': 'Utah Hockey Club'},
                {'abbrev': 'VAN', 'name': 'Vancouver Canucks'},
                {'abbrev': 'VGK', 'name': 'Vegas Golden Knights'},
                {'abbrev': 'WPG', 'name': 'Winnipeg Jets'},
                {'abbrev': 'WSH', 'name': 'Washington Capitals'}
            ]
    
    def clear_cache(self):
        """
        Clears all cached data to ensure fresh data on next fetch.
        Handles permission errors gracefully.
        """
        if os.path.exists(self.cache_dir):
            try:
                # Try to remove individual files first - often helps with permission issues
                for filename in os.listdir(self.cache_dir):
                    file_path = os.path.join(self.cache_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"Warning: Could not remove {file_path}: {e}")
                
                # Try to remove the directory itself
                try:
                    shutil.rmtree(self.cache_dir)
                except Exception as e:
                    print(f"Warning: Could not remove cache directory: {e}")
                    # Create a new directory if we couldn't remove the old one
                    if not os.path.exists(self.cache_dir):
                        os.makedirs(self.cache_dir)
                
                print("✓ Cache cleared successfully")
                return True
                
            except Exception as e:
                print(f"Warning: Error clearing cache: {e}")
                # Ensure the cache directory exists even if clearing failed
                if not os.path.exists(self.cache_dir):
                    os.makedirs(self.cache_dir)
                return False
        
        # Cache directory didn't exist, create it
        self._ensure_cache_dir()
        return True
    
    def fetch_team_roster(self, team_abbr: str, season: Optional[str] = None) -> List[Dict]:
        """
        Fetches the roster for a specific team.
        
        Args:
            team_abbr: Three-letter team abbreviation (e.g., 'TOR', 'MTL')
            season: Season in format YYYYYYYY (e.g., '20242025'), defaults to current
            
        Returns:
            List of player dictionaries with basic info
        """
        if season is None:
            season = self.current_season
            
        cache_file = os.path.join(self.cache_dir, f"roster_{team_abbr}_{season}.json")
        
        if self._cache_is_valid(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass  # If there's any issue loading cache, fetch fresh data
            
        try:
            url = f"{self.base_url}/roster/{team_abbr}/{season}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            roster_data = response.json()
            
            # Save to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(roster_data, f, ensure_ascii=False, indent=2)
                
            return roster_data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching roster for {team_abbr} ({season}): {e}")
            return []
    
    def fetch_player_stats(self, player_id: int, include_previous=True) -> Dict:
        """
        Fetches detailed statistics for a specific player.
        Extracts and flattens the most relevant stats for fantasy analysis.
        
        Args:
            player_id: NHL player ID number
            include_previous: Whether to include previous season stats
            
        Returns:
            Dictionary containing simplified player statistics
        """
        cache_file = os.path.join(self.cache_dir, f"player_{player_id}.json")
        
        if self._cache_is_valid(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    # Return the simplified version if it exists
                    if 'current_season' in cached_data:
                        return cached_data
                    # Otherwise process the cached raw data
                    return self._extract_current_season_stats(cached_data)
            except Exception:
                pass
            
        try:
            # Fetch player landing page which contains career stats
            url = f"{self.base_url}/player/{player_id}/landing"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            player_data = response.json()
            
            # Extract and simplify current season stats
            simplified_data = self._extract_current_season_stats(player_data)
            
            # Save simplified version to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(simplified_data, f, ensure_ascii=False, indent=2)
                
            return simplified_data
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching stats for player {player_id}: {e}")
            return {}
    
    def _extract_current_season_stats(self, player_data: Dict) -> Dict:
        """
        Extract and flatten current season statistics from complex API response.
        
        Args:
            player_data: Raw player data from API
            
        Returns:
            Simplified dictionary with current season stats
        """
        current_season = self.current_season
        current_stats = {}
        
        # Try to get from featuredStats first (most recent data)
        if 'featuredStats' in player_data:
            featured = player_data['featuredStats']
            if 'regularSeason' in featured:
                reg_season = featured['regularSeason']
                if 'subSeason' in reg_season:
                    current_stats = reg_season['subSeason']
        
        # If not found, look in seasonTotals array
        if not current_stats and 'seasonTotals' in player_data:
            for season_data in player_data['seasonTotals']:
                if (season_data.get('season') == current_season and 
                    season_data.get('leagueAbbrev') == 'NHL' and
                    season_data.get('gameTypeId') == 2):  # Regular season
                    current_stats = season_data
                    break
        
        # Build simplified result
        result = {
            'current_season': current_stats if current_stats else {},
            'playerId': player_data.get('playerId'),
            'position': player_data.get('position'),
            'currentTeamAbbrev': player_data.get('currentTeamAbbrev'),
            'fullName': f"{player_data.get('firstName', {}).get('default', '')} {player_data.get('lastName', {}).get('default', '')}".strip()
        }
        
        return result

    def fetch_all_players(self) -> List[Dict]:
        """
        Fetches all active NHL players by combining rosters from all teams.
        Returns simplified player data with current season stats.
        
        Returns:
            List of player dictionaries with basic info and stats
        """
        all_players = []
        teams = self.fetch_all_teams()
        
        print(f"Fetching player data for {len(teams)} teams...")
        
        for i, team in enumerate(teams):
            team_abbr = team.get('abbrev')
            if not team_abbr:
                continue
                
            print(f"[{i+1}/{len(teams)}] Fetching roster for {team_abbr}...")
            roster = self.fetch_team_roster(team_abbr)
            
            # Handle different roster formats
            roster_players = []
            if 'forwards' in roster and 'defensemen' in roster and 'goalies' in roster:
                # Grouped format
                roster_players.extend(roster.get('forwards', []))
                roster_players.extend(roster.get('defensemen', []))
                roster_players.extend(roster.get('goalies', []))
            elif isinstance(roster, list):
                # Flat list format
                roster_players = roster
            
            # Process each player
            for player in roster_players:
                player_id = player.get('id')
                if not player_id:
                    continue
                
                # Build simplified player object
                player_obj = {
                    'id': player_id,
                    'name': player.get('name', {}).get('default', '') if isinstance(player.get('name'), dict) else player.get('name', ''),
                    'firstName': player.get('firstName', {}).get('default', '') if isinstance(player.get('firstName'), dict) else player.get('firstName', ''),
                    'lastName': player.get('lastName', {}).get('default', '') if isinstance(player.get('lastName'), dict) else player.get('lastName', ''),
                    'position': player.get('positionCode', player.get('position', 'F')),
                    'team': team_abbr,
                    'sweaterNumber': player.get('sweaterNumber', player.get('jerseyNumber', ''))
                }
                
                all_players.append(player_obj)
        
        print(f"✓ Fetched {len(all_players)} players from {len(teams)} teams")
        print(f"  (Stats will be loaded as needed)")
        
        return all_players
    
    def save_to_json(self, data: List[Dict], filepath: str) -> bool:
        """
        Saves player data to a JSON file for future use or sharing.
        
        Args:
            data: List of player dictionaries to save
            filepath: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            print(f"Successfully saved data to {filepath}")
            return True
        except Exception as e:
            print(f"Error saving to JSON: {e}")
            return False
    
    def save_to_csv(self, data: List[Dict], filepath: str) -> bool:
        """
        Saves player data to a CSV file.
        
        Args:
            data: List of player dictionaries to save
            filepath: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        if not data:
            print("No data to save")
            return False
            
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as file:
                # Get all unique keys from all dictionaries
                fieldnames = set()
                for player in data:
                    fieldnames.update(player.keys())
                fieldnames = sorted(list(fieldnames))
                
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            print(f"Successfully saved data to {filepath}")
            return True
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False
    
    def parse_price_csv(self, filepath: str, debug: bool = False) -> Dict[str, float]:
        """
        Robust CSV price parser.
        Handles rows like:
          Makar C.,30,9
          Connor McDavid,14.5
          "Name","30","9"
        Skips common header rows and survives BOM/header issues.
        Only extracts player names and prices, no fantasy points.
        """
        player_prices = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                # Remove BOM if present
                if content.startswith('\ufeff'):
                    content = content[1:]
                lines = [ln for ln in content.splitlines() if ln.strip()]
                reader = csv.reader(lines)
                row_count = 0
                price_format_detected = None

                # Debug info for price entries
                parsed_entries = []
                
                for row in reader:
                    row_count += 1
                    if not row or not row[0].strip():
                        continue
                        
                    # Skip header-like rows
                    first_cell = row[0].strip().lower()
                    if any(h in first_cell for h in ['hráč', 'player', 'name', 'cena', 'price']):
                        if debug:
                            print(f"Skipping header row: {row}")
                        continue
                    # Skip comment lines
                    if first_cell.startswith('//') or first_cell.startswith('#'):
                        if debug:
                            print(f"Skipping comment row: {row}")
                        continue

                    name = row[0].strip()
                    price = None

                    # Auto-detect price format if we haven't already
                    if price_format_detected is None and len(row) >= 2:
                        # Check if using "30,9" comma format (3 columns: Name, Whole, Decimal)
                        if len(row) >= 3 and re.match(r'^\d+$', row[1].strip()) and re.match(r'^\d+$', row[2].strip()):
                            price_format_detected = "split_decimal"
                        # Check if using "30.9" or "30,9" format in a single cell (2 columns: Name, Price)
                        elif re.match(r'^[\d\.\,]+$', row[1].strip()):
                            price_format_detected = "single_cell"
                        
                        if debug and price_format_detected:
                            print(f"✓ Detected price format: {price_format_detected}")

                    # Try formats:
                    # 1) Name, whole, decimal  -> ["Makar C.", "30", "9"] = 30.9
                    if (price_format_detected == "split_decimal" or price_format_detected is None) and \
                       len(row) >= 3 and re.match(r'^\d+$', row[1].strip()) and re.match(r'^\d+$', row[2].strip()):
                        try:
                            price = float(f"{row[1].strip()}.{row[2].strip()}")
                        except Exception:
                            price = None
                    # 2) Name, price_with_comma_or_dot -> ["Connor McDavid", "14,5"] or ["Name","14.5"]
                    elif (price_format_detected == "single_cell" or price_format_detected is None) and len(row) >= 2:
                        price_str = row[1].strip().replace(',', '.')
                        # Remove any non-digit except dot
                        price_str = re.sub(r'[^\d\.]', '', price_str)
                        try:
                            price = float(price_str)
                        except Exception:
                            price = None

                    if price is None:
                        if debug:
                            print(f"⚠️  Could not parse price on row {row_count}: {row}")
                        continue

                    # Store player name and price only - no fantasy points
                    # Also store all common name variations
                    player_prices[name] = price
                    player_prices[name.lower()] = price
                    
                    # Generate additional name variants for better matching
                    variants = self._generate_name_variants(name)
                    for variant in variants:
                        if variant not in player_prices:
                            player_prices[variant] = price
                    
                    parsed_entries.append({"name": name, "price": price})
                    
                    if debug and row_count <= 5:
                        print(f"✓ Parsed: {name} = ${price}M (variants: {len(variants)})")

            # Save parsed data for debugging
            debug_file = filepath.replace('.csv', '_parsed.json').replace('.txt', '_parsed.json')
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_entries, f, ensure_ascii=False, indent=2)

            print(f"\n✓ Processed {len(parsed_entries)} unique player prices from {filepath}")
            print(f"✓ Created {len(player_prices)} total name variants for matching")
            print(f"✓ Debug file saved: {debug_file}")
            
            return player_prices

        except FileNotFoundError:
            print(f"❌ Error: File {filepath} not found")
            return {}
        except Exception as e:
            print(f"❌ Error parsing price CSV: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _normalize_name(self, name: str) -> str:
        """Return a normalized name for comparison."""
        if not name:
            return ''
        # Normalize unicode, remove diacritics
        name = unicodedata.normalize('NFKD', name)
        name = ''.join(ch for ch in name if not unicodedata.combining(ch))
        # Lowercase, remove special chars, keep alphanumerics and spaces
        name = name.lower().replace('.', ' ').replace(',', ' ')
        name = re.sub(r'[^a-z0-9\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def _generate_name_variants(self, name: str) -> List[str]:
        """
        Generate multiple variants of a player name for flexible matching
        Includes handling for common NHL name formats
        """
        variants = set()
        
        # Original name is always included
        if name:
            variants.add(name.lower())
            
        # Normalize the name for basic processing
        norm_name = self._normalize_name(name)
        if norm_name and norm_name != name.lower():
            variants.add(norm_name)
            
        # Split into tokens for additional processing
        tokens = norm_name.split() if norm_name else []
        
        if len(tokens) >= 2:
            # Last name + first initial (common format)
            variants.add(f"{tokens[-1]} {tokens[0][0]}")
            
            # First initial + last name
            variants.add(f"{tokens[0][0]} {tokens[-1]}")
            
            # Last name only
            variants.add(tokens[-1])
            
            # First name only
            variants.add(tokens[0])
            
            # First name + last name initial
            variants.add(f"{tokens[0]} {tokens[-1][0]}")
            
            # Common hockey format: Last name + first initial
            variants.add(f"{tokens[-1]} {tokens[0][0]}")
            
            # Last name + First initial with dot (Makar C.) - THIS IS THE PREFERRED FORMAT
            variants.add(f"{tokens[-1]} {tokens[0][0]}.")
            
        # Try with different spaces/formats
        for v in list(variants):
            variants.add(v.replace(' ', ''))  # No spaces
            variants.add(v.replace(' ', '.'))  # Dots instead of spaces
            
        # Return filtered list without empty strings
        return list(v for v in variants if v)

    def _extract_player_name(self, player: Dict, name_key: str = 'name') -> str:
        """Extract player name from dictionary with fallbacks and convert to price file format."""
        # Try primary key first
        name = player.get(name_key, '')
        
        # Try common fallbacks if primary is empty
        if not name:
            # Try fullName
            name = player.get('fullName', '')
            if not name:
                name = player.get('full_name', '')
            
            # If still no name, try building from first and last name
            if not name:
                first_name = ''
                last_name = ''
                
                # Try API format with nested dictionaries
                firstName_obj = player.get('firstName')
                if isinstance(firstName_obj, dict):
                    first_name = firstName_obj.get('default', '')
                elif isinstance(firstName_obj, str):
                    first_name = firstName_obj
                
                lastName_obj = player.get('lastName')
                if isinstance(lastName_obj, dict):
                    last_name = lastName_obj.get('default', '')
                elif isinstance(lastName_obj, str):
                    last_name = lastName_obj
                
                # Try alternative keys
                if not first_name:
                    first_name = player.get('first_name', '')
                if not last_name:
                    last_name = player.get('last_name', '')
                
                if first_name and last_name:
                    name = f"{first_name} {last_name}"
        
        # Now convert to "LastName FirstInitial." format for matching with price file
        if name and ' ' in name:
            parts = name.strip().split()
            if len(parts) >= 2:
                # For names like "Connor McDavid", convert to "McDavid C."
                first_initial = parts[0][0].upper()
                last_name = parts[-1].capitalize()
                formatted_name = f"{last_name} {first_initial}."
                return formatted_name
                
        return name

    def create_common_player_mappings(self) -> Dict[str, str]:
        """
        Create a mapping for common NHL stars with different name formats
        Maps standard name formats to the formats typically used in the price file
        """
        # Map common NHL star names to their likely price file format
        common_mappings = {
            "connor mcdavid": "mcdavid c.",
            "cale makar": "makar c.",
            "auston matthews": "matthews a.",
            "david pastrnak": "pastrňák d.",
            "kirill kaprizov": "kaprizov k.",
            "nathan mackinnon": "mackinnon n.",
            "tage thompson": "thompson t.",
            "nikita kucherov": "kucherov n.",
            "alexander ovechkin": "ovechkin a.",
            "brady tkachuk": "tkachuk b.",
            "matthew tkachuk": "tkachuk m.",
            "leon draisaitl": "draisaitl l.",
            "mitch marner": "marner m.",
            "quinn hughes": "hughes q.",
            "jack hughes": "hughes j.",
            "luke hughes": "hughes l.",
            "sidney crosby": "crosby s.",
            "steven stamkos": "stamkos s.",
            "elias pettersson": "pettersson e.",
            "mark scheifele": "scheifele m.",
            "sebastian aho": "aho s.",
            "patrik laine": "laine p.",
            "aleksander barkov": "barkov a.",
            "brad marchand": "marchand b.",
        }
        return common_mappings

    def match_players_with_prices(
        self,
        players: List[Dict],
        prices: Dict[str, float],
        name_key: str = 'name',
        debug_output: bool = True
    ) -> List[Dict]:
        """
        Enhanced matching logic that uses multiple strategies to match player names with prices.
        Only adds price information, not points.
        
        Args:
            players: List of player dictionaries
            prices: Dictionary mapping player names to prices
            name_key: Key in player dict containing the name
            debug_output: Whether to print detailed debug info
            
        Returns:
            List of players with prices added
        """
        matched_count = 0
        direct_matches = 0
        variant_matches = 0
        common_matches = 0
        fuzzy_matches = 0
        unmatched_players = []
        
        # Store match details for debugging
        match_details = []
        
        # Create mapping for common NHL stars
        common_player_map = self.create_common_player_mappings()
        
        # First pass: Build efficient lookup structures
        # 1. Normalize all price names for faster lookups
        norm_prices = {}
        for price_name, price in prices.items():
            # Store original to normalized mapping
            norm_name = self._normalize_name(price_name)
            if norm_name:
                norm_prices[norm_name] = price
                
            # Store lowercase version
            norm_prices[price_name.lower()] = price
        
        # Process each player
        for player in players:
            # Get player name using helper or direct access
            player_name = self._extract_player_name(player, name_key)
            if not player_name:
                unmatched_players.append("<no-name>")
                continue
                
            # Ensure player has a name for downstream code
            if not player.get('name'):
                player['name'] = player_name
            
            match_type = None
            matched_variant = None
            matched_price = None
            
            # STRATEGY 1: Direct match with original price keys (case-sensitive)
            if player_name in prices:
                player['cena'] = prices[player_name]
                matched_count += 1
                direct_matches += 1
                match_type = "direct"
                matched_variant = player_name
                matched_price = prices[player_name]
                match_details.append({
                    "player": player_name,
                    "match_type": "direct",
                    "matched_with": player_name,
                    "price": prices[player_name]
                })
                continue
            
            # STRATEGY 2: Case-insensitive match
            if player_name.lower() in prices:
                player['cena'] = prices[player_name.lower()]
                matched_count += 1
                direct_matches += 1
                match_type = "case_insensitive"
                matched_variant = player_name.lower()
                matched_price = prices[player_name.lower()]
                match_details.append({
                    "player": player_name,
                    "match_type": "case_insensitive",
                    "matched_with": player_name.lower(),
                    "price": prices[player_name.lower()]
                })
                continue
                
            # STRATEGY 3: Try common player mappings for NHL stars
            norm_player_name = self._normalize_name(player_name).lower()
            if norm_player_name in common_player_map:
                mapped_name = common_player_map[norm_player_name]
                if mapped_name in norm_prices:
                    player['cena'] = norm_prices[mapped_name]
                    matched_count += 1
                    common_matches += 1
                    match_type = "common_map"
                    matched_variant = mapped_name
                    matched_price = norm_prices[mapped_name]
                    match_details.append({
                        "player": player_name,
                        "match_type": "common_map",
                        "mapped_to": mapped_name,
                        "price": norm_prices[mapped_name]
                    })
                    continue
        
            # STRATEGY 4: Try all name variants
            name_variants = self._generate_name_variants(player_name)
            variant_matched = False
            
            for variant in name_variants:
                if variant in norm_prices:
                    player['cena'] = norm_prices[variant]
                    matched_count += 1
                    variant_matches += 1
                    variant_matched = True
                    match_type = "variant"
                    matched_variant = variant
                    matched_price = norm_prices[variant]
                    match_details.append({
                        "player": player_name,
                        "match_type": "variant",
                        "matched_variant": variant,
                        "price": norm_prices[variant]
                    })
                    break
                    
            if variant_matched:
                continue
                
            # STRATEGY 5: Try fuzzy matching as last resort
            best_match = None
            best_ratio = 0.0
            
            for price_name in norm_prices.keys():
                ratio = difflib.SequenceMatcher(None, norm_player_name, price_name).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = price_name
            
            # Accept fuzzy match if confidence is high enough (>75% to be more lenient)
            if best_match and best_ratio > 0.75:
                player['cena'] = norm_prices[best_match]
                matched_count += 1
                fuzzy_matches += 1
                match_type = "fuzzy"
                matched_variant = best_match
                matched_price = norm_prices[best_match]
                match_details.append({
                    "player": player_name,
                    "match_type": "fuzzy",
                    "matched_with": best_match,
                    "confidence": best_ratio,
                    "price": norm_prices[best_match]
                })
                continue
            
            # No match found - collect for reporting
            unmatched_players.append(player_name)
            match_details.append({
                "player": player_name,
                "match_type": "unmatched",
                "variants_tried": name_variants[:3],
                "original_name": player.get(name_key, ''),
                "api_first_name": player.get('firstName', {}).get('default', '') if isinstance(player.get('firstName'), dict) else '',
                "api_last_name": player.get('lastName', {}).get('default', '') if isinstance(player.get('lastName'), dict) else ''
            })
        
        # Save match details to file for debugging
        try:
            with open("player_price_matching.json", "w", encoding="utf-8") as f:
                json.dump({
                    "total_players": len(players),
                    "matched_count": matched_count,
                    "direct_matches": direct_matches,
                    "variant_matches": variant_matches,
                    "common_matches": common_matches,
                    "fuzzy_matches": fuzzy_matches,
                    "unmatched_count": len(unmatched_players),
                    "details": match_details
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if debug_output:
                print(f"Warning: Could not save match details: {e}")
        
        # Print match statistics
        if debug_output:
            print(f"\n✓ Matched prices for {matched_count}/{len(players)} players")
            print(f"  - Direct matches: {direct_matches}")
            print(f"  - Common player matches: {common_matches}")
            print(f"  - Variant matches: {variant_matches}")
            print(f"  - Fuzzy matches: {fuzzy_matches}")
            if unmatched_players:
                print(f"\n⚠️  {len(unmatched_players)} unmatched players. First 10:")
                for p in unmatched_players[:10]:
                    print(f"    - {p}")
                print(f"    (See player_price_matching.json for full details)")
                
        return players
    
    def get_team_schedule(self, date: str) -> Dict[str, List[str]]:
        """
        Get teams playing on a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary mapping date to list of team abbreviations
        """
        cache_file = os.path.join(self.cache_dir, f"schedule_{date}.json")
        
        if self._cache_is_valid(cache_file, max_age_hours=6):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        try:
            url = f"{self.base_url}/schedule/{date}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            schedule_data = response.json()
            
            teams_playing = []
            
            # Extract teams from game data
            for game_week in schedule_data.get('gameWeek', []):
                for game in game_week.get('games', []):
                    away_team = game.get('awayTeam', {}).get('abbrev')
                    home_team = game.get('homeTeam', {}).get('abbrev')
                    
                    if away_team:
                        teams_playing.append(away_team)
                    if home_team:
                        teams_playing.append(home_team)
            
            result = {date: list(set(teams_playing))}
            
            # Save to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            return result
        except requests.exceptions.RequestException as e:
            print(f"Error fetching schedule for {date}: {e}")
            return {date: []}
    
    def filter_teams_by_gameday(self, players: List[Dict], teams: List[str]) -> List[Dict]:
        """
        Filter players to only include those from specified teams.
        
        Args:
            players: List of player dictionaries
            teams: List of team abbreviations to keep
            
        Returns:
            Filtered list of players
        """
        if not teams:
            return players
        
        teams_upper = [t.upper() for t in teams]
        filtered = [
            p for p in players 
            if p.get('team', '').upper() in teams_upper
        ]
        
        print(f"Filtered to {len(filtered)} players from teams: {', '.join(teams)}")
        return filtered
