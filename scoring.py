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
        """Initialize with standard scoring rules."""
        # Common scoring values for all positions
        self.common_scoring = {
            # Basic stats
            'goal': 0,  # Base value, position-specific values are used instead
            'assist': 0,  # Base value, position-specific values are used instead
            
            # Special goals
            'power_play_goal': 10,
            'short_handed_goal': 16,
            'game_winning_goal': 10,
            'hat_trick': 12,
            
            # Special assists
            'power_play_assist': 5,
            'short_handed_assist': 8,
            
            # Penalties
            'penalty_2min': -0.5,
            'penalty_5min': -2,
            'misconduct_10min': -4,
            'game_misconduct': -8,
            
            # Other
            'shot': 1,
            'hit': 1,
            'blocked_shot': 0,  # Base value, position-specific values are used
            'plus_minus': 2,  # Per +1 rating
            
            # Team results
            'team_win_regulation': 3,
            'team_win_overtime': 2,
            'team_win_shootout': 1,
            'team_loss_regulation': -3,
            'team_loss_overtime': -2,
            'team_loss_shootout': -1
        }
        
        # Position-specific scoring adjustments
        self.forward_scoring = {
            'goal': 12,  # Even strength goal for forward
            'assist': 6,  # Even strength assist for forward
            'blocked_shot': 2  # Lower value for forwards blocking shots
        }
        
        self.defense_scoring = {
            'goal': 20,  # Even strength goal for defender
            'assist': 8,  # Even strength assist for defender
            'blocked_shot': 4  # Higher value for defenders blocking shots
        }
        
        self.goalie_scoring = {
            'win': 6,
            'loss': -6,
            'saved_shot': 1,
            'cleared_goal': -4,
            'shutout': 12,
            'goal_against': -3,
            'overtime_loss': -3
        }

    def calculate_player_value(self, player: Dict[str, Any]) -> float:
        """
        Calculate a value score for a player based on their statistics, position, and price.
        
        Process:
        1. Extract statistics from player data
        2. Calculate fantasy points based on scoring rules
        3. Divide by price to get value per dollar
        
        Args:
            player: Dictionary containing player stats, position, and price
            
        Returns:
            Value score (fantasy_points / price)
        """
        # Determine player position
        position = self._normalize_position(player.get('position', 'F'))
        
        # Get stats dictionary
        stats = self._extract_stats(player)
        
        # Get price
        price = player.get('cena', 0)
        
        # Skip if no stats or invalid price
        if not stats or price <= 0:
            return 0.0
        
        # Check if player has played any games
        games = self._get_stat(stats, 'games', 'gamesPlayed', 'games_played')
        
        # If no games played, check if ANY stat is non-zero
        if games == 0:
            has_any_stat = any([
                self._get_stat(stats, 'goals', 'g') > 0,
                self._get_stat(stats, 'assists', 'a') > 0,
                self._get_stat(stats, 'shots', 's') > 0,
                self._get_stat(stats, 'hits', 'h') > 0,
                self._get_stat(stats, 'blocked_shots', 'bs') > 0,
                abs(self._get_stat(stats, 'plus_minus')) > 0
            ])
            
            if not has_any_stat:
                return 0.0
            
            # Assume at least 1 game for calculation purposes
            games = 1
        
        # STEP 1: Calculate fantasy points from stats based on position
        if position == 'G':
            fantasy_points = self._calculate_goalie_points(stats)
        elif position == 'D':
            fantasy_points = self._calculate_defender_points(stats)
        else:  # Forward (F)
            fantasy_points = self._calculate_forward_points(stats)
        
        # If no fantasy points, return 0
        if fantasy_points <= 0:
            return 0.0
        
        # STEP 2: Calculate value per dollar
        # Higher fantasy points and lower price = better value
        value_score = fantasy_points / price if price > 0 else 0
        
        return value_score
    
    def _calculate_forward_stat_value(self, stats: Dict) -> float:
        """
        Calculate statistical value for a forward based on fantasy scoring weights.
        This is NOT fantasy points - it's a weighted measure of statistical production.
        
        Args:
            stats: Player statistics dictionary
            
        Returns:
            Statistical value score
        """
        value = 0.0
        
        # Weight each stat by its fantasy importance
        # Goals are worth more than assists, PP goals more than EV goals, etc.
        
        # Basic production
        value += self._get_stat(stats, 'goals', 'g') * 12.0
        value += self._get_stat(stats, 'assists', 'a') * 6.0
        
        # Special situations (bonus value)
        value += self._get_stat(stats, 'power_play_goals', 'ppg') * 10.0
        value += self._get_stat(stats, 'short_handed_goals', 'shg') * 16.0
        value += self._get_stat(stats, 'game_winning_goals', 'gwg') * 10.0
        value += self._get_stat(stats, 'hat_tricks') * 12.0
        
        value += self._get_stat(stats, 'power_play_assists', 'ppa') * 5.0
        value += self._get_stat(stats, 'short_handed_assists', 'sha') * 8.0
        
        # Peripheral stats (smaller weights)
        value += self._get_stat(stats, 'shots', 'shots_on_goal', 's') * 1.0
        value += self._get_stat(stats, 'hits', 'h') * 1.0
        value += self._get_stat(stats, 'blocked_shots', 'blocked', 'bs') * 2.0
        
        # Plus/minus (can be positive or negative)
        plus_minus = self._get_stat(stats, 'plus_minus', 'plus_minus_rating', 'plusminus')
        value += plus_minus * 2.0
        
        # Penalties (negative value)
        value += self._get_stat(stats, 'penalty_minutes_2', 'pim_2') * -0.5
        value += self._get_stat(stats, 'penalty_minutes_5', 'pim_5') * -2.0
        value += self._get_stat(stats, 'penalty_minutes_10', 'pim_10', 'misconduct') * -4.0
        value += self._get_stat(stats, 'game_misconduct', 'gm_penalty') * -8.0
        
        return max(0, value)  # Don't return negative values
    
    def _calculate_defender_stat_value(self, stats: Dict) -> float:
        """
        Calculate statistical value for a defender based on fantasy scoring weights.
        Defenders get higher value for goals and blocked shots.
        
        Args:
            stats: Player statistics dictionary
            
        Returns:
            Statistical value score
        """
        value = 0.0
        
        # Defenders get premium for scoring
        value += self._get_stat(stats, 'goals', 'g') * 20.0
        value += self._get_stat(stats, 'assists', 'a') * 8.0
        
        # Special situations
        value += self._get_stat(stats, 'power_play_goals', 'ppg') * 10.0
        value += self._get_stat(stats, 'short_handed_goals', 'shg') * 16.0
        value += self._get_stat(stats, 'game_winning_goals', 'gwg') * 10.0
        value += self._get_stat(stats, 'hat_tricks') * 12.0
        
        value += self._get_stat(stats, 'power_play_assists', 'ppa') * 5.0
        value += self._get_stat(stats, 'short_handed_assists', 'sha') * 8.0
        
        # Defensive stats (higher value for defenders)
        value += self._get_stat(stats, 'shots', 'shots_on_goal', 's') * 1.0
        value += self._get_stat(stats, 'hits', 'h') * 1.0
        value += self._get_stat(stats, 'blocked_shots', 'blocked', 'bs') * 4.0  # Higher for defenders
        
        # Plus/minus
        plus_minus = self._get_stat(stats, 'plus_minus', 'plus_minus_rating', 'plusminus')
        value += plus_minus * 2.0
        
        # Penalties
        value += self._get_stat(stats, 'penalty_minutes_2', 'pim_2') * -0.5
        value += self._get_stat(stats, 'penalty_minutes_5', 'pim_5') * -2.0
        value += self._get_stat(stats, 'penalty_minutes_10', 'pim_10', 'misconduct') * -4.0
        value += self._get_stat(stats, 'game_misconduct', 'gm_penalty') * -8.0
        
        return max(0, value)
    
    def _calculate_goalie_stat_value(self, stats: Dict) -> float:
        """
        Calculate statistical value for a goaltender based on fantasy scoring weights.
        Goalies are valued differently - wins, saves, and save percentage matter most.
        
        Args:
            stats: Player statistics dictionary
            
        Returns:
            Statistical value score
        """
        value = 0.0
        
        # Wins are crucial for goalies
        value += self._get_stat(stats, 'wins', 'w') * 6.0
        value += self._get_stat(stats, 'losses', 'l') * -6.0
        value += self._get_stat(stats, 'overtime_losses', 'otl', 'ot') * -3.0
        
        # Saves and shutouts
        value += self._get_stat(stats, 'saves', 'saved_shots', 'sv') * 1.0
        value += self._get_stat(stats, 'shutouts', 'so') * 12.0
        
        # Goals against (negative)
        value += self._get_stat(stats, 'goals_against', 'ga') * -3.0
        value += self._get_stat(stats, 'cleared_goals', 'expected_goals') * -4.0
        
        return max(0, value)
    
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
        
        # Get stats dictionary, which might be nested differently depending on data source
        stats = self._extract_stats(player)
        
        # Skip if no stats available
        if not stats:
            return 0.0
            
        # Calculate based on position
        if position == 'G':
            return self._calculate_goalie_points(stats)
        elif position == 'D':
            return self._calculate_defender_points(stats)
        else:  # Forward (F)
            return self._calculate_forward_points(stats)
    
    def _normalize_position(self, position: str) -> str:
        """
        Normalize position to standard format: F (forward), D (defense), G (goalie).
        
        Args:
            position: Raw position string from data
            
        Returns:
            Normalized position code
        """
        pos = position.upper().strip()
        
        # Goalie variations
        if pos in ['G', 'GOALIE', 'GOALKEEPER', 'B', 'BRANKÁR', 'BRANKAŘ']:
            return 'G'
        
        # Defender variations
        if pos in ['D', 'DEFENSE', 'DEFENDER', 'DEFENSEMAN', 'DEFENCEMAN', 'O', 'OBRANCA', 'OBRÁNCE']:
            return 'D'
        
        # Forward variations
        if pos in ['F', 'C', 'LW', 'RW', 'FORWARD', 'ATTACKER', 'CENTER', 'WING', 'Ú', 'ÚTOČNÍK', 'UTOČNÍK']:
            return 'F'
        
        # Default to forward if unknown
        return 'F'
    
    def _extract_stats(self, player: Dict[str, Any]) -> Dict:
        """
        Extract statistics from player object, handling different data structures.
        
        Args:
            player: Player dictionary with stats
            
        Returns:
            Dictionary of stats
        """
        # Check for nested 'stats' dictionary first
        if 'stats' in player and isinstance(player['stats'], dict):
            return player['stats']
            
        # Check for API format with current_season stats
        if 'current_season_stats' in player and isinstance(player['current_season_stats'], dict):
            return player['current_season_stats']
            
        # Check for flat structure (all stats in main dict)
        stat_keys = ['goals', 'assists', 'shots', 'hits', 'blocked_shots', 'plus_minus']
        if any(key in player for key in stat_keys):
            return player
            
        # Return empty dict if no stats found
        return {}
    
    def _calculate_forward_points(self, stats: Dict) -> float:
        """
        Calculate fantasy points for a forward.
        
        Args:
            stats: Player statistics dictionary
            
        Returns:
            Fantasy points
        """
        points = 0.0
        
        # Basic stats using forward-specific values
        points += self._get_stat(stats, 'goals', 'g') * self.forward_scoring['goal']
        points += self._get_stat(stats, 'assists', 'a') * self.forward_scoring['assist']
        
        # Special goals
        points += self._get_stat(stats, 'power_play_goals', 'ppg') * self.common_scoring['power_play_goal']
        points += self._get_stat(stats, 'short_handed_goals', 'shg') * self.common_scoring['short_handed_goal']
        points += self._get_stat(stats, 'game_winning_goals', 'gwg') * self.common_scoring['game_winning_goal']
        points += self._get_stat(stats, 'hat_tricks') * self.common_scoring['hat_trick']
        
        # Special assists
        points += self._get_stat(stats, 'power_play_assists', 'ppa') * self.common_scoring['power_play_assist']
        points += self._get_stat(stats, 'short_handed_assists', 'sha') * self.common_scoring['short_handed_assist']
        
        # Penalties
        points += self._get_stat(stats, 'penalty_minutes_2', 'pim_2') * self.common_scoring['penalty_2min']
        points += self._get_stat(stats, 'penalty_minutes_5', 'pim_5') * self.common_scoring['penalty_5min']
        points += self._get_stat(stats, 'penalty_minutes_10', 'pim_10', 'misconduct') * self.common_scoring['misconduct_10min']
        points += self._get_stat(stats, 'game_misconduct', 'gm_penalty') * self.common_scoring['game_misconduct']
        
        # Other stats
        points += self._get_stat(stats, 'shots', 'shots_on_goal', 's') * self.common_scoring['shot']
        points += self._get_stat(stats, 'hits', 'h') * self.common_scoring['hit']
        points += self._get_stat(stats, 'blocked_shots', 'blocked', 'bs') * self.forward_scoring['blocked_shot']
        
        # Plus/minus
        plus_minus = self._get_stat(stats, 'plus_minus', 'plus_minus_rating', 'plusminus')
        if plus_minus > 0:
            points += plus_minus * self.common_scoring['plus_minus']
        elif plus_minus < 0:
            points += plus_minus * self.common_scoring['plus_minus']  # Negative already included in value
        
        # Team results
        points += self._get_stat(stats, 'team_win_regulation') * self.common_scoring['team_win_regulation']
        points += self._get_stat(stats, 'team_win_overtime') * self.common_scoring['team_win_overtime']
        points += self._get_stat(stats, 'team_win_shootout') * self.common_scoring['team_win_shootout']
        points += self._get_stat(stats, 'team_loss_regulation') * self.common_scoring['team_loss_regulation']
        points += self._get_stat(stats, 'team_loss_overtime') * self.common_scoring['team_loss_overtime']
        points += self._get_stat(stats, 'team_loss_shootout') * self.common_scoring['team_loss_shootout']
        
        return points
    
    def _calculate_defender_points(self, stats: Dict) -> float:
        """
        Calculate fantasy points for a defender.
        
        Args:
            stats: Player statistics dictionary
            
        Returns:
            Fantasy points
        """
        points = 0.0
        
        # Basic stats using defender-specific values
        points += self._get_stat(stats, 'goals', 'g') * self.defense_scoring['goal']
        points += self._get_stat(stats, 'assists', 'a') * self.defense_scoring['assist']
        
        # Special goals
        points += self._get_stat(stats, 'power_play_goals', 'ppg') * self.common_scoring['power_play_goal']
        points += self._get_stat(stats, 'short_handed_goals', 'shg') * self.common_scoring['short_handed_goal']
        points += self._get_stat(stats, 'game_winning_goals', 'gwg') * self.common_scoring['game_winning_goal']
        points += self._get_stat(stats, 'hat_tricks') * self.common_scoring['hat_trick']
        
        # Special assists
        points += self._get_stat(stats, 'power_play_assists', 'ppa') * self.common_scoring['power_play_assist']
        points += self._get_stat(stats, 'short_handed_assists', 'sha') * self.common_scoring['short_handed_assist']
        
        # Penalties
        points += self._get_stat(stats, 'penalty_minutes_2', 'pim_2') * self.common_scoring['penalty_2min']
        points += self._get_stat(stats, 'penalty_minutes_5', 'pim_5') * self.common_scoring['penalty_5min']
        points += self._get_stat(stats, 'penalty_minutes_10', 'pim_10', 'misconduct') * self.common_scoring['misconduct_10min']
        points += self._get_stat(stats, 'game_misconduct', 'gm_penalty') * self.common_scoring['game_misconduct']
        
        # Other stats
        points += self._get_stat(stats, 'shots', 'shots_on_goal', 's') * self.common_scoring['shot']
        points += self._get_stat(stats, 'hits', 'h') * self.common_scoring['hit']
        points += self._get_stat(stats, 'blocked_shots', 'blocked', 'bs') * self.defense_scoring['blocked_shot']
        
        # Plus/minus
        plus_minus = self._get_stat(stats, 'plus_minus', 'plus_minus_rating', 'plusminus')
        if plus_minus > 0:
            points += plus_minus * self.common_scoring['plus_minus']
        elif plus_minus < 0:
            points += plus_minus * self.common_scoring['plus_minus']  # Negative already included in value
        
        # Team results
        points += self._get_stat(stats, 'team_win_regulation') * self.common_scoring['team_win_regulation']
        points += self._get_stat(stats, 'team_win_overtime') * self.common_scoring['team_win_overtime']
        points += self._get_stat(stats, 'team_win_shootout') * self.common_scoring['team_win_shootout']
        points += self._get_stat(stats, 'team_loss_regulation') * self.common_scoring['team_loss_regulation']
        points += self._get_stat(stats, 'team_loss_overtime') * self.common_scoring['team_loss_overtime']
        points += self._get_stat(stats, 'team_loss_shootout') * self.common_scoring['team_loss_shootout']
        
        return points
    
    def _calculate_goalie_points(self, stats: Dict) -> float:
        """
        Calculate fantasy points for a goaltender.
        
        Args:
            stats: Player statistics dictionary
            
        Returns:
            Fantasy points
        """
        points = 0.0
        
        # Goalie-specific stats
        points += self._get_stat(stats, 'wins', 'w') * self.goalie_scoring['win']
        points += self._get_stat(stats, 'losses', 'l') * self.goalie_scoring['loss']
        points += self._get_stat(stats, 'overtime_losses', 'otl', 'ot') * self.goalie_scoring['overtime_loss']
        points += self._get_stat(stats, 'shutouts', 'so') * self.goalie_scoring['shutout']
        points += self._get_stat(stats, 'goals_against', 'ga') * self.goalie_scoring['goal_against']
        
        # Special goalie stats from images
        points += self._get_stat(stats, 'saves', 'saved_shots', 'sv') * self.goalie_scoring['saved_shot']
        points += self._get_stat(stats, 'cleared_goals', 'expected_goals') * self.goalie_scoring['cleared_goal']
        
        return points
    
    def calculate_game_score(self, player: Dict[str, Any]) -> float:
        """
        Calculate GameScore (GS) per game for a player.
        Based on NHL GameScore formula using available stats.
        
        Formula:
        - Goals: 0.75
        - Assists (Primary+Secondary combined): 0.625 average
        - Shots: 0.075
        - Blocked Shots: 0.05
        - Hits: 0.05 (proxy for physical engagement)
        - Plus/Minus: 0.15 per +1
        
        Args:
            player: Player dictionary with stats
            
        Returns:
            GameScore per game
        """
        stats = self._extract_stats(player)
        
        if not stats:
            return 0.0
        
        games = self._get_stat(stats, 'games', 'gamesPlayed', 'games_played')
        
        if games == 0:
            return 0.0
        
        # Get stats
        goals = self._get_stat(stats, 'goals', 'g')
        assists = self._get_stat(stats, 'assists', 'a')
        shots = self._get_stat(stats, 'shots', 'shots_on_goal', 's')
        blocked_shots = self._get_stat(stats, 'blocked_shots', 'blocked', 'bs')
        hits = self._get_stat(stats, 'hits', 'h')
        plus_minus = self._get_stat(stats, 'plus_minus', 'plus_minus_rating', 'plusminus')
        
        # Calculate GameScore components
        gs = 0.0
        gs += goals * 0.75
        gs += assists * 0.625  # Average of primary (0.7) and secondary (0.55)
        gs += shots * 0.075
        gs += blocked_shots * 0.05
        gs += hits * 0.05  # Proxy for physical engagement
        gs += plus_minus * 0.15
        
        # Penalties (negative contribution)
        pim_2 = self._get_stat(stats, 'penalty_minutes_2', 'pim_2')
        pim_5 = self._get_stat(stats, 'penalty_minutes_5', 'pim_5')
        pim_10 = self._get_stat(stats, 'penalty_minutes_10', 'pim_10')
        
        # Assume each penalty is one infraction
        gs += (pim_2 / 2) * -0.15  # 2-min penalties
        gs += (pim_5 / 5) * -0.15  # 5-min penalties
        gs += (pim_10 / 10) * -0.15  # 10-min penalties
        
        # Return per-game average
        return gs / games if games > 0 else 0.0
    
    def calculate_fantasy_points_per_game(self, player: Dict[str, Any]) -> float:
        """
        Calculate fantasy points per game for a player.
        
        Args:
            player: Player dictionary
            
        Returns:
            Fantasy points per game
        """
        stats = self._extract_stats(player)
        
        if not stats:
            return 0.0
        
        games = self._get_stat(stats, 'games', 'gamesPlayed', 'games_played')
        
        if games == 0:
            return 0.0
        
        # Calculate total fantasy points
        position = self._normalize_position(player.get('position', 'F'))
        
        if position == 'G':
            total_fp = self._calculate_goalie_stat_value(stats)
        elif position == 'D':
            total_fp = self._calculate_defender_stat_value(stats)
        else:
            total_fp = self._calculate_forward_stat_value(stats)
        
        return total_fp / games if games > 0 else 0.0

    def _get_stat(self, stats: Dict, *keys: str) -> Union[int, float]:
        """
        Get a stat value safely from a stats dictionary.
        Tries multiple possible keys.
        
        Args:
            stats: Statistics dictionary
            keys: Multiple possible keys to check
            
        Returns:
            Stat value or 0 if not found
        """
        for key in keys:
            if key in stats:
                val = stats[key]
                try:
                    # Convert to float and handle None/empty values
                    if val is None:
                        return 0
                    return float(val)
                except (ValueError, TypeError):
                    # If conversion fails, try next key
                    continue
                    
        # No valid stat found
        return 0