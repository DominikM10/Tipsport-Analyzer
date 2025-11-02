"""
Fantasy Hockey Scoring Module
Implements comprehensive scoring rules for NHL fantasy contests.
"""

from typing import Dict, Any, List, Union


class FantasyScorer:
    """
    Calculates fantasy value based on comprehensive scoring rules.
    Handles different scoring categories for forwards, defenders, and goalies.
    """
    
    def __init__(self):
        """Initialize with standard scoring rules based on Tipsport scoring system."""
        # Common scoring values for all positions
        self.common_scoring = {
            # Penalties (same for all positions)
            'penalty_2min': -2,
            'penalty_5min': -4,
            'misconduct_10min': -2,
            'game_misconduct': -6,
            
            # Shots and hits
            'shot': 2,
            'hit': 2,
            'plus_minus': 2,  # Per +/- point
            
            # Team results (same for all)
            'team_win_regulation': 4,
            'team_win_overtime': 2,
            'team_win_shootout': 2,
            'team_loss_regulation': -4,
            'team_loss_overtime': -2,
            'team_loss_shootout': -2
        }
        
        # Forward-specific scoring
        self.forward_scoring = {
            'goal_even': 12,
            'goal_pp': 10,
            'goal_sh': 16,
            'game_winning_goal': 4,
            'hat_trick': 6,
            'assist_even': 12,
            'assist_pp': 12,
            'assist_sh': 12,
            'blocked_shot': 4
        }
        
        # Defender-specific scoring
        self.defense_scoring = {
            'goal_even': 20,
            'goal_pp': 18,
            'goal_sh': 24,
            'game_winning_goal': 4,
            'hat_trick': 6,
            'assist_even': 12,
            'assist_pp': 12,
            'assist_sh': 12,
            'blocked_shot': 4
        }
        
        # Goalie-specific scoring (based on Tipsport rules)
        self.goalie_scoring = {
            'goal_even': 40,
            'goal_pp': 40,
            'goal_sh': 40,
            'game_winning_goal': 4,
            'hat_trick': 6,
            'assist_even': 12,
            'assist_pp': 12,
            'assist_sh': 12,
            'win': 6,  # Výhry
            'loss': -6,  # Prehry
            'shutout': 10,  # Vychytané nuly
            'save': 1,  # Chytené strely - CRITICAL FOR GOALIE SCORING
            'goal_against': -4  # Obdržané góly
        }

    def calculate_player_value(self, player: Dict[str, Any]) -> float:
        """
        Calculate a value score for a player based on their statistics, position, and price.
        
        Args:
            player: Dictionary containing player stats, position, and price
            
        Returns:
            Value score (fantasy_points / price)
        """
        # Determine player position
        position = self._normalize_position(player.get('position', 'F'))
        
        # Get price
        price = player.get('cena', 0)
        
        # Skip if invalid price
        if price <= 0:
            return 0.0
        
        # Calculate fantasy points
        fantasy_points = self.calculate_points(player)
        
        # If no fantasy points, return 0
        if fantasy_points <= 0:
            return 0.0
        
        # Calculate value per dollar
        value_score = fantasy_points / price
        
        return value_score
    
    def calculate_points(self, player: Dict[str, Any]) -> float:
        """
        Calculate fantasy points for a player based on position and stats.
        
        Args:
            player: Dictionary containing player stats and info
            
        Returns:
            Total fantasy points
        """
        # Determine player position
        position = self._normalize_position(player.get('position', 'F'))
        
        # Get stats dictionary (combine current and previous seasons)
        stats = self._extract_combined_stats(player)
        
        # Debug output for Strome
        if 'Strome' in player.get('name', '') and player.get('team') == 'ANA':
            print(f"\n[DEBUG] calculate_points for {player.get('name')}:")
            print(f"  Games: {stats.get('gamesPlayed', 0):.1f}")
            print(f"  Goals: {stats.get('goals', 0):.1f}")
            print(f"  Assists: {stats.get('assists', 0):.1f}")
        
        # Skip if no stats available
        if not stats:
            return 0.0
            
        # Calculate base fantasy points based on position
        if position == 'G':
            base_points = self._calculate_goalie_points(stats)
        elif position == 'D':
            base_points = self._calculate_defender_points(stats)
        else:  # Forward
            base_points = self._calculate_forward_points(stats)
        
        # Debug output for Strome
        if 'Strome' in player.get('name', '') and player.get('team') == 'ANA':
            print(f"  Fantasy Points: {base_points:.1f}\n")
        
        return base_points
    
    def _calculate_dynamic_weights(self, current_stats: Dict) -> tuple:
        """
        Calculate dynamic weighting based on current season progress using sigmoid curve.
        This creates a smooth, natural transition that accelerates in mid-season.
        
        Early season (0-20 games): Slow shift from 15% to ~35% current
        Mid season (20-50 games): Rapid transition to ~75% current  
        Late season (50-82 games): Gradual approach to 92% current
        
        Uses sigmoid function: weight = L / (1 + e^(-k*(x - x0)))
        where L=max weight, k=steepness, x0=midpoint
        
        Args:
            current_stats: Current season statistics
            
        Returns:
            Tuple of (current_weight, previous_weight)
        """
        import math
        
        games_played = self._get_stat(current_stats, 'gamesPlayed')
        
        if games_played <= 0:
            # No games played yet - rely heavily on previous season
            return 0.15, 0.85
        
        # Sigmoid parameters for smooth transition
        # L = 0.92 (max weight at 92% current season)
        # k = 0.08 (steepness - higher = more abrupt transition)
        # x0 = 35 (inflection point at game 35, mid-season)
        L = 0.92
        k = 0.08
        x0 = 35
        
        # Sigmoid function for natural S-curve
        games_capped = min(games_played, 82)
        current_weight = L / (1 + math.exp(-k * (games_capped - x0)))
        
        # Ensure minimum of 15% current weight even at start
        current_weight = max(0.15, current_weight)
        
        previous_weight = 1.0 - current_weight
        
        return current_weight, previous_weight
    
    def _apply_rookie_amplification(self, current_stats: Dict) -> Dict:
        """
        Apply dynamic amplification to rookie stats based on games played.
        Uses logarithmic decay so amplification decreases as sample size grows.
        
        Logic:
        - With few games (1-10): High amplification (1.35-1.25) due to small sample
        - With moderate games (10-40): Medium amplification (1.25-1.10)  
        - With many games (40-82): Low amplification (1.10-1.05)
        
        Formula: amp = 1.05 + 0.30 * e^(-games/20)
        This creates exponential decay from 1.35 to 1.05
        
        Args:
            current_stats: Current season statistics
            
        Returns:
            Amplified statistics dictionary
        """
        import math
        
        amplified = current_stats.copy()
        games_played = self._get_stat(current_stats, 'gamesPlayed')
        
        if games_played <= 0:
            # No games played - maximum amplification
            amplification = 1.40
        else:
            # Exponential decay from 1.35 to 1.05 as games increase
            # Formula: 1.05 + 0.30 * e^(-games/20)
            # At 1 game: ~1.35
            # At 10 games: ~1.23
            # At 20 games: ~1.16  
            # At 40 games: ~1.09
            # At 82 games: ~1.05
            decay_rate = 20  # Controls how fast amplification decreases
            amplification = 1.05 + 0.30 * math.exp(-games_played / decay_rate)
        
        numeric_keys = ['goals', 'assists', 'points', 'shots', 'hits', 'blockedShots',
                       'powerPlayGoals', 'powerPlayPoints', 'shorthandedGoals', 'shorthandedPoints',
                       'gameWinningGoals', 'plusMinus', 'pim', 'wins', 'losses', 'shutouts',
                       'goalsAgainst', 'saves']
        
        for key in numeric_keys:
            if key in amplified and isinstance(amplified[key], (int, float)):
                amplified[key] = amplified[key] * amplification
        
        return amplified
    
    def _extract_combined_stats(self, player: Dict) -> Dict:
        """
        Extract and combine statistics from current and previous seasons.
        Uses dynamic weighting based on season progress:
        - Early season: 30% current, 70% previous
        - Late season: 90% current, 10% previous
        - Rookies: 115% amplification of current stats
        
        Args:
            player: Player dictionary with stats
            
        Returns:
            Combined dictionary of stats
        """
        current_season = "20252026"
        previous_season = "20242025"
        
        current_stats = {}
        previous_stats = {}
        
        # Priority 1: Check for featuredStats.regularSeason.subSeason (current season)
        if 'featuredStats' in player and isinstance(player['featuredStats'], dict):
            featured = player['featuredStats']
            if 'regularSeason' in featured and isinstance(featured['regularSeason'], dict):
                if 'subSeason' in featured['regularSeason']:
                    current_stats = featured['regularSeason']['subSeason']
        
        # Priority 2: Check seasonTotals array
        if 'seasonTotals' in player and isinstance(player['seasonTotals'], list):
            for season_data in player['seasonTotals']:
                season = str(season_data.get('season', ''))
                league = season_data.get('leagueAbbrev', '')
                game_type = season_data.get('gameTypeId', 0)
                
                # Only count NHL regular season games
                if league != 'NHL' or game_type != 2:
                    continue
                
                if season == current_season:
                    # Merge current season stats
                    for key, value in season_data.items():
                        if key not in current_stats and value is not None:
                            current_stats[key] = value
                elif season == previous_season:
                    # Store previous season stats
                    previous_stats = season_data
        
        # Priority 3: Check for current_season or stats dictionary
        if not current_stats:
            if 'current_season' in player and isinstance(player['current_season'], dict):
                current_stats = player['current_season']
            elif 'stats' in player and isinstance(player['stats'], dict):
                current_stats = player['stats']
            elif 'current_season_stats' in player and isinstance(player['current_season_stats'], dict):
                current_stats = player['current_season_stats']
        
        # Debug for Strome
        if 'Strome' in player.get('name', '') and player.get('team') == 'ANA':
            print(f"\n[DEBUG] _extract_combined_stats for {player.get('name')}:")
            print(f"  Found current_stats: {bool(current_stats)}")
            if current_stats:
                print(f"    Current GP: {current_stats.get('gamesPlayed', 0)}")
            print(f"  Found previous_stats: {bool(previous_stats)}")
            if previous_stats:
                print(f"    Previous GP: {previous_stats.get('gamesPlayed', 0)}")
        
        # If we have no current stats, return empty
        if not current_stats:
            return {}
        
        # Combine current and previous seasons with dynamic weighting
        combined = current_stats.copy()
        
        current_games = self._get_stat(current_stats, 'gamesPlayed')
        
        if previous_stats and current_games > 0:
            # Calculate dynamic weight based on current season progress
            current_weight, previous_weight = self._calculate_dynamic_weights(current_stats)
            
            previous_games = self._get_stat(previous_stats, 'gamesPlayed')
            
            # Combine numeric stats using PER-GAME rates, not totals
            # This prevents inflated stats from combining season totals
            numeric_keys = ['goals', 'assists', 'points', 'shots', 'hits', 'blockedShots',
                          'powerPlayGoals', 'powerPlayPoints', 'shorthandedGoals', 'shorthandedPoints',
                          'gameWinningGoals', 'plusMinus', 'pim', 'wins', 'losses', 'shutouts',
                          'goalsAgainst', 'saves']
            
            for key in numeric_keys:
                current_val = self._get_stat(current_stats, key)
                previous_val = self._get_stat(previous_stats, key)
                
                # Calculate per-game rates
                current_per_game = current_val / current_games if current_games > 0 else 0
                previous_per_game = previous_val / previous_games if previous_games > 0 else 0
                
                # Weighted average of per-game rates
                combined_per_game = (current_per_game * current_weight) + (previous_per_game * previous_weight)
                
                # Project to current season games played (not full 82!)
                combined[key] = combined_per_game * current_games
            
            # Games played uses current season only
            combined['gamesPlayed'] = current_games
        else:
            # Rookie or no previous stats - use current stats only (no amplification for now)
            combined = current_stats.copy()
        
        return combined
    
    def _calculate_forward_points(self, stats: Dict) -> float:
        """Calculate fantasy points for a forward."""
        points = 0.0
        
        # Goals (need to estimate even strength vs PP vs SH)
        total_goals = self._get_stat(stats, 'goals', 'g')
        pp_goals = self._get_stat(stats, 'powerPlayGoals', 'ppg')
        sh_goals = self._get_stat(stats, 'shorthandedGoals', 'shg')
        
        # Even strength goals = total - PP - SH
        even_goals = max(0, total_goals - pp_goals - sh_goals)
        
        points += even_goals * self.forward_scoring['goal_even']
        points += pp_goals * self.forward_scoring['goal_pp']
        points += sh_goals * self.forward_scoring['goal_sh']
        
        # Game winning goals
        gwg = self._get_stat(stats, 'gameWinningGoals', 'gwg')
        points += gwg * self.forward_scoring['game_winning_goal']
        
        # Hat tricks (estimate: 1 hat trick per 10 goals for high scorers)
        if total_goals >= 30:
            hat_tricks = max(1, int(total_goals / 10))
            points += hat_tricks * self.forward_scoring['hat_trick']
        
        # Assists (estimate distribution like goals)
        total_assists = self._get_stat(stats, 'assists', 'a')
        pp_assists = self._get_stat(stats, 'powerPlayPoints', 'ppp') - pp_goals  # PP points minus PP goals
        pp_assists = max(0, pp_assists)
        sh_assists = self._get_stat(stats, 'shorthandedPoints', 'shp') - sh_goals
        sh_assists = max(0, sh_assists)
        
        even_assists = max(0, total_assists - pp_assists - sh_assists)
        
        points += even_assists * self.forward_scoring['assist_even']
        points += pp_assists * self.forward_scoring['assist_pp']
        points += sh_assists * self.forward_scoring['assist_sh']
        
        # Shots
        shots = self._get_stat(stats, 'shots', 'sog', 's')
        points += shots * self.common_scoring['shot']
        
        # Hits
        hits = self._get_stat(stats, 'hits', 'h')
        points += hits * self.common_scoring['hit']
        
        # Blocked shots
        blocked = self._get_stat(stats, 'blockedShots', 'blocked', 'bs')
        points += blocked * self.forward_scoring['blocked_shot']
        
        # Plus/minus
        plus_minus = self._get_stat(stats, 'plusMinus', 'plus_minus_rating', 'plusminus')
        points += plus_minus * self.common_scoring['plus_minus']
        
        # Penalties (negative points)
        pim = self._get_stat(stats, 'pim', 'penaltyMinutes')
        # Estimate distribution: mostly 2-min, some 5-min, rare misconducts
        two_min_penalties = int(pim * 0.8 / 2)  # 80% are 2-min
        five_min_penalties = int(pim * 0.15 / 5)  # 15% are 5-min
        misconduct = int(pim * 0.05 / 10)  # 5% are misconducts
        
        points += two_min_penalties * self.common_scoring['penalty_2min']
        points += five_min_penalties * self.common_scoring['penalty_5min']
        points += misconduct * self.common_scoring['misconduct_10min']
        
        return max(0, points)
    
    def _calculate_defender_points(self, stats: Dict) -> float:
        """Calculate fantasy points for a defender (higher goal values)."""
        points = 0.0
        
        # Goals (higher value for defenders)
        total_goals = self._get_stat(stats, 'goals', 'g')
        pp_goals = self._get_stat(stats, 'powerPlayGoals', 'ppg')
        sh_goals = self._get_stat(stats, 'shorthandedGoals', 'shg')
        
        even_goals = max(0, total_goals - pp_goals - sh_goals)
        
        points += even_goals * self.defense_scoring['goal_even']
        points += pp_goals * self.defense_scoring['goal_pp']
        points += sh_goals * self.defense_scoring['goal_sh']
        
        # Game winning goals
        gwg = self._get_stat(stats, 'gameWinningGoals', 'gwg')
        points += gwg * self.defense_scoring['game_winning_goal']
        
        # Hat tricks (rare for defenders)
        if total_goals >= 20:
            hat_tricks = max(1, int(total_goals / 15))
            points += hat_tricks * self.defense_scoring['hat_trick']
        
        # Assists
        total_assists = self._get_stat(stats, 'assists', 'a')
        pp_assists = self._get_stat(stats, 'powerPlayPoints', 'ppp') - pp_goals
        pp_assists = max(0, pp_assists)
        sh_assists = self._get_stat(stats, 'shorthandedPoints', 'shp') - sh_goals
        sh_assists = max(0, sh_assists)
        
        even_assists = max(0, total_assists - pp_assists - sh_assists)
        
        points += even_assists * self.defense_scoring['assist_even']
        points += pp_assists * self.defense_scoring['assist_pp']
        points += sh_assists * self.defense_scoring['assist_sh']
        
        # Shots
        shots = self._get_stat(stats, 'shots', 'sog', 's')
        points += shots * self.common_scoring['shot']
        
        # Hits
        hits = self._get_stat(stats, 'hits', 'h')
        points += hits * self.common_scoring['hit']
        
        # Blocked shots (important for defenders)
        blocked = self._get_stat(stats, 'blockedShots', 'blocked', 'bs')
        points += blocked * self.defense_scoring['blocked_shot']
        
        # Plus/minus
        plus_minus = self._get_stat(stats, 'plusMinus', 'plus_minus_rating', 'plusminus')
        points += plus_minus * self.common_scoring['plus_minus']
        
        # Penalties
        pim = self._get_stat(stats, 'pim', 'penaltyMinutes')
        two_min_penalties = int(pim * 0.8 / 2)
        five_min_penalties = int(pim * 0.15 / 5)
        misconduct = int(pim * 0.05 / 10)
        
        points += two_min_penalties * self.common_scoring['penalty_2min']
        points += five_min_penalties * self.common_scoring['penalty_5min']
        points += misconduct * self.common_scoring['misconduct_10min']
        
        return max(0, points)
    
    def _calculate_goalie_points(self, stats: Dict) -> float:
        """Calculate fantasy points for a goaltender based on Tipsport rules."""
        points = 0.0
        
        # Wins and losses
        wins = self._get_stat(stats, 'wins', 'w')
        losses = self._get_stat(stats, 'losses', 'l')
        
        points += wins * self.goalie_scoring['win']
        points += losses * self.goalie_scoring['loss']
        
        # Shutouts (Vychytané nuly)
        shutouts = self._get_stat(stats, 'shutouts', 'so')
        points += shutouts * self.goalie_scoring['shutout']
        
        # Saves (Chytené strely) - CRITICAL!
        # Try to get saves directly, or calculate from shotsAgainst - goalsAgainst
        saves = self._get_stat(stats, 'saves', 'sv', 'savesTotal')
        if saves == 0:
            shots_against = self._get_stat(stats, 'shotsAgainst', 'sa')
            goals_against = self._get_stat(stats, 'goalsAgainst', 'ga')
            saves = max(0, shots_against - goals_against)
        points += saves * self.goalie_scoring['save']
        
        # Goals against (Obdržané góly)
        goals_against = self._get_stat(stats, 'goalsAgainst', 'ga')
        points += goals_against * self.goalie_scoring['goal_against']
        
        # Goalies can also score goals and assists (rare but valuable)
        total_goals = self._get_stat(stats, 'goals', 'g')
        if total_goals > 0:
            pp_goals = self._get_stat(stats, 'powerPlayGoals', 'ppg')
            sh_goals = self._get_stat(stats, 'shorthandedGoals', 'shg')
            even_goals = max(0, total_goals - pp_goals - sh_goals)
            
            points += even_goals * self.goalie_scoring['goal_even']
            points += pp_goals * self.goalie_scoring['goal_pp']
            points += sh_goals * self.goalie_scoring['goal_sh']
        
        total_assists = self._get_stat(stats, 'assists', 'a')
        if total_assists > 0:
            # Estimate assist distribution
            pp_assists = max(0, self._get_stat(stats, 'powerPlayPoints', 'ppp') - self._get_stat(stats, 'powerPlayGoals', 'ppg'))
            sh_assists = max(0, self._get_stat(stats, 'shorthandedPoints', 'shp') - self._get_stat(stats, 'shorthandedGoals', 'shg'))
            even_assists = max(0, total_assists - pp_assists - sh_assists)
            
            points += even_assists * self.goalie_scoring['assist_even']
            points += pp_assists * self.goalie_scoring['assist_pp']
            points += sh_assists * self.goalie_scoring['assist_sh']
        
        return max(0, points)
    
    def calculate_correlation_bonus(
        self, 
        player: Dict[str, Any], 
        top_performers: List[Dict],
        position: str
    ) -> float:
        """
        Calculate bonus points based on unmapped statistics compared to top performers.
        Awards 0-2 points per stat category based on player's performance vs. top 10.
        
        Args:
            player: Player dictionary
            top_performers: List of top 10 players in same position
            position: Player position (G, D, F)
            
        Returns:
            Correlation bonus points (capped at 10)
        """
        if not top_performers:
            return 0.0
        
        bonus = 0.0
        stats = self._extract_combined_stats(player)
        
        if not stats:
            return 0.0
        
        # Get games played for per-game calculations
        games = max(1, self._get_stat(stats, 'gamesPlayed', 'games', 'gp'))
        
        # Stats to consider for correlation
        if position == 'G':
            # Goalie-specific unmapped stats
            save_pct = self._get_stat(stats, 'savePctg', 'savePercentage', 'svPct') * 100
            gaa = self._get_stat(stats, 'goalsAgainstAverage', 'gaa')
            
            # Calculate averages from top performers
            top_save_pcts = [self._get_stat(self._extract_combined_stats(p), 'savePctg', 'savePercentage') * 100 
                           for p in top_performers if self._get_stat(self._extract_combined_stats(p), 'savePctg') > 0]
            top_gaas = [self._get_stat(self._extract_combined_stats(p), 'goalsAgainstAverage', 'gaa')
                       for p in top_performers if self._get_stat(self._extract_combined_stats(p), 'goalsAgainstAverage') > 0]
            
            if top_save_pcts and save_pct > 0:
                avg_save_pct = sum(top_save_pcts) / len(top_save_pcts)
                if save_pct >= avg_save_pct * 1.05:  # 5% better
                    bonus += 2.0
                elif save_pct >= avg_save_pct:
                    bonus += 1.0
            
            if top_gaas and gaa > 0:
                avg_gaa = sum(top_gaas) / len(top_gaas)
                if gaa <= avg_gaa * 0.95:  # 5% better (lower is better)
                    bonus += 2.0
                elif gaa <= avg_gaa:
                    bonus += 1.0
        
        else:  # F or D
            # Shooting percentage
            shooting_pct = self._get_stat(stats, 'shootingPctg', 'shootingPercentage', 'sPct') * 100
            
            # Time on ice per game
            toi = self._get_stat(stats, 'avgToi', 'timeOnIcePerGame', 'toi')
            
            # Faceoff percentage (mostly for forwards)
            fo_pct = self._get_stat(stats, 'faceoffWinningPctg', 'faceOffPct') * 100
            
            # Calculate averages
            top_shooting = [self._get_stat(self._extract_combined_stats(p), 'shootingPctg') * 100
                          for p in top_performers if self._get_stat(self._extract_combined_stats(p), 'shootingPctg') > 0]
            
            if top_shooting and shooting_pct > 0:
                avg_shooting = sum(top_shooting) / len(top_shooting)
                if shooting_pct >= avg_shooting * 1.1:  # 10% better
                    bonus += 2.0
                elif shooting_pct >= avg_shooting:
                    bonus += 1.0
            
            # Points per game bonus
            points_per_game = self._get_stat(stats, 'points') / games
            top_ppg = [self._get_stat(self._extract_combined_stats(p), 'points') / max(1, self._get_stat(self._extract_combined_stats(p), 'gamesPlayed'))
                      for p in top_performers if self._get_stat(self._extract_combined_stats(p), 'gamesPlayed') > 0]
            
            if top_ppg and points_per_game > 0:
                avg_ppg = sum(top_ppg) / len(top_ppg)
                if points_per_game >= avg_ppg * 1.1:
                    bonus += 2.0
                elif points_per_game >= avg_ppg:
                    bonus += 1.0
        
        # Cap total bonus at 10 points
        return min(10.0, bonus)
    
    def _normalize_position(self, position: str) -> str:
        """
        Normalize position to standard format: F (forward), D (defense), G (goalie).
        """
        pos = position.upper().strip()
        
        if pos in ['G', 'GOALIE', 'GOALKEEPER', 'B', 'BRANKÁR', 'BRANKAŘ']:
            return 'G'
        
        if pos in ['D', 'DEFENSE', 'DEFENDER', 'DEFENSEMAN', 'DEFENCEMAN', 'O', 'OBRANCA', 'OBRÁNCE']:
            return 'D'
        
        # All forward positions map to 'F'
        if pos in ['F', 'C', 'LW', 'RW', 'FORWARD', 'ATTACKER', 'CENTER', 'WING', 'Ú', 'ÚTOČNÍK', 'UTOČNÍK', 'L', 'R']:
            return 'F'
        
        return 'F'  # Default
    
    def _get_stat(self, stats: Dict, *keys: str) -> Union[int, float]:
        """
        Get a stat value safely from a stats dictionary.
        Tries multiple possible keys and returns 0 for any missing or invalid values.
        """
        for key in keys:
            if key in stats:
                value = stats[key]
                if value is not None:
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        continue
        return 0.0

    def calculate_game_score(self, player: Dict[str, Any]) -> float:
        """Calculate GameScore metric for advanced optimization."""
        stats = self._extract_combined_stats(player)
        if not stats:
            return 0.0
        
        position = self._normalize_position(player.get('position', 'F'))
        games = max(1, self._get_stat(stats, 'gamesPlayed', 'games', 'gp'))
        
        if position == 'G':
            # Goalie GameScore
            wins = self._get_stat(stats, 'wins', 'w')
            saves = self._get_stat(stats, 'saves', 'sv')
            ga = self._get_stat(stats, 'goalsAgainst', 'ga')
            
            gs = (wins * 0.5) + (saves * 0.01) - (ga * 0.2)
            return gs / games
        else:
            # Skater GameScore
            goals = self._get_stat(stats, 'goals', 'g')
            assists = self._get_stat(stats, 'assists', 'a')
            shots = self._get_stat(stats, 'shots', 's')
            blocked = self._get_stat(stats, 'blockedShots', 'bs')
            
            gs = (goals * 0.75) + (assists * 0.7) + (shots * 0.05) + (blocked * 0.05)
            return gs / games
    
    def calculate_fantasy_points_per_game(self, player: Dict[str, Any]) -> float:
        """Calculate fantasy points per game."""
        stats = self._extract_combined_stats(player)
        if not stats:
            return 0.0
        
        games = max(1, self._get_stat(stats, 'gamesPlayed', 'games', 'gp'))
        total_points = self.calculate_points(player)
        
        return total_points / games

    def generate_scoring_breakdown(self, player: Dict[str, Any]) -> str:
        """
        Generate a detailed breakdown of how fantasy points were calculated for a player.
        Shows each stat category and the points awarded.
        
        Args:
            player: Player dictionary with stats
            
        Returns:
            Formatted string showing the scoring breakdown
        """
        position = self._normalize_position(player.get('position', 'F'))
        stats = self._extract_combined_stats(player)
        
        if not stats:
            return f"No stats available for {player.get('name', 'Unknown')}"
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"FANTASY POINTS BREAKDOWN: {player.get('name', 'Unknown')}")
        lines.append(f"Position: {position} | Team: {player.get('team', '???')}")
        lines.append("=" * 60)
        lines.append("")
        
        total_points = 0.0
        
        if position == 'G':
            # Goalie breakdown
            lines.append("GOALIE SCORING:")
            lines.append("-" * 60)
            
            wins = self._get_stat(stats, 'wins', 'w')
            if wins > 0:
                pts = wins * self.goalie_scoring['win']
                lines.append(f"  Wins: {int(wins)} × {self.goalie_scoring['win']} = {pts:.1f} pts")
                total_points += pts
            
            losses = self._get_stat(stats, 'losses', 'l')
            if losses > 0:
                pts = losses * self.goalie_scoring['loss']
                lines.append(f"  Losses: {int(losses)} × {self.goalie_scoring['loss']} = {pts:.1f} pts")
                total_points += pts
            
            shutouts = self._get_stat(stats, 'shutouts', 'so')
            if shutouts > 0:
                pts = shutouts * self.goalie_scoring['shutout']
                lines.append(f"  Shutouts: {int(shutouts)} × {self.goalie_scoring['shutout']} = {pts:.1f} pts")
                total_points += pts
            
            # Saves (calculated or direct)
            saves = self._get_stat(stats, 'saves', 'sv', 'savesTotal')
            if saves == 0:
                shots_against = self._get_stat(stats, 'shotsAgainst', 'sa')
                ga = self._get_stat(stats, 'goalsAgainst', 'ga')
                saves = max(0, shots_against - ga)
            if saves > 0:
                pts = saves * self.goalie_scoring['save']
                lines.append(f"  Saves: {int(saves)} × {self.goalie_scoring['save']} = {pts:.1f} pts")
                total_points += pts
            
            ga = self._get_stat(stats, 'goalsAgainst', 'ga')
            if ga > 0:
                pts = ga * self.goalie_scoring['goal_against']
                lines.append(f"  Goals Against: {int(ga)} × {self.goalie_scoring['goal_against']} = {pts:.1f} pts")
                total_points += pts
                
        else:
            # Skater breakdown (Forward or Defense)
            scoring_dict = self.defense_scoring if position == 'D' else self.forward_scoring
            pos_name = "DEFENDER" if position == 'D' else "FORWARD"
            
            lines.append(f"{pos_name} SCORING:")
            lines.append("-" * 60)
            
            # Goals
            total_goals = self._get_stat(stats, 'goals', 'g')
            pp_goals = self._get_stat(stats, 'powerPlayGoals', 'ppg')
            sh_goals = self._get_stat(stats, 'shorthandedGoals', 'shg')
            even_goals = max(0, total_goals - pp_goals - sh_goals)
            
            if even_goals > 0:
                pts = even_goals * scoring_dict['goal_even']
                lines.append(f"  Even Strength Goals: {int(even_goals)} × {scoring_dict['goal_even']} = {pts:.1f} pts")
                total_points += pts
            
            if pp_goals > 0:
                pts = pp_goals * scoring_dict['goal_pp']
                lines.append(f"  Power Play Goals: {int(pp_goals)} × {scoring_dict['goal_pp']} = {pts:.1f} pts")
                total_points += pts
            
            if sh_goals > 0:
                pts = sh_goals * scoring_dict['goal_sh']
                lines.append(f"  Short-Handed Goals: {int(sh_goals)} × {scoring_dict['goal_sh']} = {pts:.1f} pts")
                total_points += pts
            
            gwg = self._get_stat(stats, 'gameWinningGoals', 'gwg')
            if gwg > 0:
                pts = gwg * scoring_dict['game_winning_goal']
                lines.append(f"  Game Winning Goals: {int(gwg)} × {scoring_dict['game_winning_goal']} = {pts:.1f} pts")
                total_points += pts
            
            # Hat tricks (estimated)
            if total_goals >= 30:
                hat_tricks = max(1, int(total_goals / 10))
                pts = hat_tricks * scoring_dict['hat_trick']
                lines.append(f"  Hat Tricks (est): {hat_tricks} × {scoring_dict['hat_trick']} = {pts:.1f} pts")
                total_points += pts
            
            # Assists
            total_assists = self._get_stat(stats, 'assists', 'a')
            pp_assists = max(0, self._get_stat(stats, 'powerPlayPoints', 'ppp') - pp_goals)
            sh_assists = max(0, self._get_stat(stats, 'shorthandedPoints', 'shp') - sh_goals)
            even_assists = max(0, total_assists - pp_assists - sh_assists)
            
            if even_assists > 0:
                pts = even_assists * scoring_dict['assist_even']
                lines.append(f"  Even Strength Assists: {int(even_assists)} × {scoring_dict['assist_even']} = {pts:.1f} pts")
                total_points += pts
            
            if pp_assists > 0:
                pts = pp_assists * scoring_dict['assist_pp']
                lines.append(f"  Power Play Assists: {int(pp_assists)} × {scoring_dict['assist_pp']} = {pts:.1f} pts")
                total_points += pts
            
            if sh_assists > 0:
                pts = sh_assists * scoring_dict['assist_sh']
                lines.append(f"  Short-Handed Assists: {int(sh_assists)} × {scoring_dict['assist_sh']} = {pts:.1f} pts")
                total_points += pts
            
            # Shots
            shots = self._get_stat(stats, 'shots', 'sog', 's')
            if shots > 0:
                pts = shots * self.common_scoring['shot']
                lines.append(f"  Shots on Goal: {int(shots)} × {self.common_scoring['shot']} = {pts:.1f} pts")
                total_points += pts
            
            # Hits
            hits = self._get_stat(stats, 'hits', 'h')
            if hits > 0:
                pts = hits * self.common_scoring['hit']
                lines.append(f"  Hits: {int(hits)} × {self.common_scoring['hit']} = {pts:.1f} pts")
                total_points += pts
            
            # Blocked shots
            blocked = self._get_stat(stats, 'blockedShots', 'blocked', 'bs')
            if blocked > 0:
                pts = blocked * scoring_dict['blocked_shot']
                lines.append(f"  Blocked Shots: {int(blocked)} × {scoring_dict['blocked_shot']} = {pts:.1f} pts")
                total_points += pts
            
            # Plus/Minus
            plus_minus = self._get_stat(stats, 'plusMinus', 'plus_minus_rating', 'plusminus')
            if plus_minus != 0:
                pts = plus_minus * self.common_scoring['plus_minus']
                lines.append(f"  Plus/Minus: {int(plus_minus):+d} × {self.common_scoring['plus_minus']} = {pts:.1f} pts")
                total_points += pts
            
            # Penalties
            pim = self._get_stat(stats, 'pim', 'penaltyMinutes')
            if pim > 0:
                two_min = int(pim * 0.8 / 2)
                five_min = int(pim * 0.15 / 5)
                misconduct = int(pim * 0.05 / 10)
                
                if two_min > 0:
                    pts = two_min * self.common_scoring['penalty_2min']
                    lines.append(f"  2-min Penalties (est): {two_min} × {self.common_scoring['penalty_2min']} = {pts:.1f} pts")
                    total_points += pts
                
                if five_min > 0:
                    pts = five_min * self.common_scoring['penalty_5min']
                    lines.append(f"  5-min Penalties (est): {five_min} × {self.common_scoring['penalty_5min']} = {pts:.1f} pts")
                    total_points += pts
                
                if misconduct > 0:
                    pts = misconduct * self.common_scoring['misconduct_10min']
                    lines.append(f"  Misconducts (est): {misconduct} × {self.common_scoring['misconduct_10min']} = {pts:.1f} pts")
                    total_points += pts
        
        lines.append("")
        lines.append("-" * 60)
        lines.append(f"TOTAL FANTASY POINTS: {total_points:.1f}")
        lines.append("=" * 60)
        
        return "\n".join(lines)