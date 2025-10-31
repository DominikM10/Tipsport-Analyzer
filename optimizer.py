"""
NHL Fantasy Lineup Optimizer
Builds optimal fantasy lineups considering budget constraints and penalty rules.
Uses dynamic programming and greedy algorithms for efficient optimization.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import itertools


@dataclass
class LineupConstraints:
    """Defines the constraints and rules for building a fantasy lineup."""
    base_budget: float = 100.0  # Base budget in millions
    max_budget: float = 200.0   # Absolute maximum (no hard limit mentioned)
    penalty_per_million: float = 0.01  # 1% penalty per million over 100
    
    # Lineup structure: 2G + 4D + 6F = 12 players
    required_positions: Dict[str, int] = None
    
    def __post_init__(self):
        if self.required_positions is None:
            self.required_positions = {
                'G': 2,   # 2 Goalkeepers
                'D': 4,   # 4 Defenders
                'F': 6    # 6 Forwards
            }


class LineupOptimizer:
    """
    Optimizes fantasy lineups by selecting the best combination of players
    within budget constraints while maximizing projected fantasy points.
    """
    
    def __init__(self, constraints: Optional[LineupConstraints] = None):
        self.constraints = constraints or LineupConstraints()
    
    def calculate_budget_penalty(self, total_cost: float) -> float:
        """
        Penalty: 1% per million over 100M base budget.
        No maximum penalty - can go as high as needed.
        """
        if total_cost <= self.constraints.base_budget:
            return 0.0
        
        overspend = total_cost - self.constraints.base_budget
        penalty = overspend * self.constraints.penalty_per_million
        
        return penalty
    
    def calculate_effective_points(
        self,
        raw_points: float,
        total_cost: float
    ) -> float:
        """
        Calculates the effective fantasy points after applying budget penalties.
        
        Args:
            raw_points: Total projected fantasy points before penalties
            total_cost: Total lineup cost
            
        Returns:
            Points after penalty adjustment
        """
        penalty = self.calculate_budget_penalty(total_cost)
        return raw_points * (1 - penalty)
    
    def normalize_position(self, position: str) -> str:
        """
        Normalizes position strings to standard format (G, D, F).
        Handles various input formats from different data sources.
        
        Args:
            position: Raw position string
            
        Returns:
            Normalized position code
        """
        pos = position.upper().strip()
        
        # Goalkeeper variations
        if pos in ['G', 'GOALIE', 'GOALKEEPER']:
            return 'G'
        
        # Defender variations
        if pos in ['D', 'DEFENSE', 'DEFENDER', 'DEFENSEMAN', 'DEFENCEMAN']:
            return 'D'
        
        # Forward/Attacker variations (all treated as 'F')
        if pos in ['F', 'C', 'LW', 'RW', 'FORWARD', 'ATTACKER', 'CENTER', 'WING', 'L', 'R']:
            return 'F'
        
        return 'F'  # Default to forward if unknown
    
    def group_players_by_position(
        self,
        players: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Organizes players into position groups for easier lineup construction.
        
        Args:
            players: List of all available players
            
        Returns:
            Dictionary mapping positions to player lists
        """
        grouped = {'G': [], 'D': [], 'F': []}
        
        for player in players:
            pos = self.normalize_position(player.get('position', 'F'))
            grouped[pos].append(player)
        
        return grouped
    
    def rank_players_by_value(
        self,
        players: List[Dict],
        sort_key: str = 'value_score'
    ) -> List[Dict]:
        """
        Ranks players by their fantasy value metrics.
        
        Args:
            players: List of player dictionaries
            sort_key: Metric to sort by ('value_score', 'projected_points', 'value_per_cost')
            
        Returns:
            Sorted list of players (best to worst)
        """
        # Ensure value_score is set (for backwards compatibility)
        for player in players:
            if 'value_score' not in player and 'projected_points' in player:
                player['value_score'] = player['projected_points']
            elif 'value_score' not in player:
                # Calculate on the fly if needed
                cost = player.get('cena', player.get('price', 1))
                points = player.get('projected_points', 0)
                
                if cost > 0:
                    player['value_score'] = points / cost
                else:
                    player['value_score'] = 0
        
        # Sort by the specified key (descending order)
        return sorted(
            players,
            key=lambda p: p.get(sort_key, 0),
            reverse=True
        )
    
    def build_greedy_lineup(
        self,
        players: List[Dict],
        max_budget: Optional[float] = None
    ) -> Tuple[List[Dict], float, float]:
        """
        Builds a lineup using a greedy algorithm - selects best value players first.
        Uses value_score which combines statistical production and price efficiency.
        
        Args:
            players: List of all available players with stats and prices
            max_budget: Maximum budget to use (defaults to constraint max)
            
        Returns:
            Tuple of (lineup, total_cost, effective_value_score)
        """
        if max_budget is None:
            max_budget = self.constraints.max_budget
            
        # Filter out players with no value score or no price
        valid_players = [
            p for p in players 
            if p.get('value_score', 0) > 0 
            and p.get('cena', 0) > 0
            and p.get('name')  # Must have a name
        ]
        
        if not valid_players:
            print("❌ Error: No valid players found with both prices and value scores!")
            print("\nDebug info:")
            print(f"  Total players: {len(players)}")
            players_with_price = [p for p in players if p.get('cena', 0) > 0]
            print(f"  Players with price: {len(players_with_price)}")
            players_with_value = [p for p in players if p.get('value_score', 0) > 0]
            print(f"  Players with value_score: {len(players_with_value)}")
            
            if players_with_price and not players_with_value:
                print("\n⚠️  Players have prices but no value scores calculated!")
                print("    Make sure calculate_all_scores() is called before optimization.")
            
            return [], 0.0, 0.0
            
        # Group and rank players by position
        grouped = self.group_players_by_position(valid_players)
        
        print(f"\nValid players by position:")
        for pos in ['G', 'D', 'F']:
            print(f"  {pos}: {len(grouped[pos])} players")
        
        for pos in grouped:
            # Rank by value_score (statistical production per dollar)
            grouped[pos] = self.rank_players_by_value(grouped[pos], 'value_score')
            
            # Print top players in each position
            if grouped[pos]:
                print(f"\nTop 3 {pos} players:")
                for i, p in enumerate(grouped[pos][:3], 1):
                    print(f"  {i}. {p.get('name')} - Value: {p.get('value_score', 0):.2f}, ${p.get('cena', 0):.1f}M")
        
        lineup = []
        total_cost = 0.0
        total_value = 0.0
        
        # Fill each position requirement greedily
        for position, count in self.constraints.required_positions.items():
            available = grouped[position]
            selected_count = 0
            
            if len(available) < count:
                print(f"⚠️  Warning: Only {len(available)} {position} players available, need {count}")
            
            for player in available:
                if selected_count >= count:
                    break
                
                cost = player.get('cena', 0)
                value = player.get('value_score', 0)
                
                # Skip invalid players
                if cost <= 0 or value <= 0:
                    continue
                
                # Check if we can afford this player
                if total_cost + cost <= max_budget:
                    lineup.append(player)
                    total_cost += cost
                    total_value += value
                    selected_count += 1
                    print(f"  Selected: {player.get('name')} ({position}) - ${cost:.1f}M, Value: {value:.2f}")
                else:
                    # Try to find a cheaper alternative
                    cheaper_found = False
                    for alt_player in available[available.index(player)+1:]:
                        alt_cost = alt_player.get('cena', 0)
                        alt_value = alt_player.get('value_score', 0)
                        
                        if alt_cost > 0 and alt_value > 0 and total_cost + alt_cost <= max_budget:
                            lineup.append(alt_player)
                            total_cost += alt_cost
                            total_value += alt_value
                            selected_count += 1
                            print(f"  Selected (budget): {alt_player.get('name')} ({position}) - ${alt_cost:.1f}M, Value: {alt_value:.2f}")
                            cheaper_found = True
                            break
                    
                    if not cheaper_found and selected_count < count:
                        print(f"  ⚠️  Could not afford {position} position #{selected_count + 1}")
            
            if selected_count < count:
                print(f"⚠️  Warning: Only selected {selected_count}/{count} {position} players")
        
        # Calculate effective value after budget penalties
        # The value score already accounts for price efficiency,
        # but we still apply budget penalty for going over base budget
        penalty = self.calculate_budget_penalty(total_cost)
        effective_value = total_value * (1 - penalty)
        
        print(f"\n✓ Lineup complete: {len(lineup)} players, ${total_cost:.2f}M, {effective_value:.2f} value")
        
        return lineup, total_cost, effective_value
    
    def optimize_lineup_iterative(
        self,
        players: List[Dict],
        iterations: int = 1000
    ) -> Tuple[List[Dict], float, float]:
        """
        Uses iterative improvement to find better lineups than greedy approach.
        Tries multiple combinations and swaps to maximize effective points.
        
        Args:
            players: List of all available players
            iterations: Number of optimization attempts
            
        Returns:
            Tuple of (best_lineup, total_cost, effective_points)
        """
        # Start with greedy baseline
        best_lineup, best_cost, best_points = self.build_greedy_lineup(players)
        
        grouped = self.group_players_by_position(players)
        
        # Try to improve through position-wise swaps
        for _ in range(iterations):
            # Create a copy of current best
            current_lineup = best_lineup.copy()
            
            # Try swapping one player from each position
            for position in self.constraints.required_positions.keys():
                position_players = [p for p in current_lineup 
                                  if self.normalize_position(p.get('position', '')) == position]
                
                if not position_players:
                    continue
                
                # Try replacing the lowest value player in this position
                current_pos_players = sorted(position_players, 
                                            key=lambda p: p.get('value_per_cost', 0))
                worst_player = current_pos_players[0]
                
                # Try alternatives from the same position
                alternatives = [p for p in grouped[position] 
                              if p not in current_lineup]
                
                for alt_player in alternatives[:5]:  # Try top 5 alternatives
                    # Calculate new lineup metrics
                    test_lineup = [p for p in current_lineup if p != worst_player]
                    test_lineup.append(alt_player)
                    
                    test_cost = sum(p.get('cena', p.get('price', 0)) for p in test_lineup)
                    test_raw_points = sum(p.get('projected_points', 0) for p in test_lineup)
                    test_effective = self.calculate_effective_points(test_raw_points, test_cost)
                    
                    # Keep if better and within budget
                    if (test_effective > best_points and 
                        test_cost <= self.constraints.max_budget):
                        best_lineup = test_lineup
                        best_cost = test_cost
                        best_points = test_effective
        
        return best_lineup, best_cost, best_points
    
    def generate_lineup_report(
        self,
        lineup: List[Dict],
        total_cost: float,
        effective_value: float
    ) -> str:
        """
        Generates a human-readable report of the lineup with all relevant details.
        
        Args:
            lineup: Selected players
            total_cost: Total lineup cost
            effective_value: Value score after penalties
            
        Returns:
            Formatted string report
        """
        raw_fantasy_points = sum(p.get('fantasy_points', 0) for p in lineup)
        raw_value = sum(p.get('value_score', 0) for p in lineup)
        penalty = self.calculate_budget_penalty(total_cost)
        penalty_fp = raw_fantasy_points * penalty
        
        report = []
        report.append("=" * 70)
        report.append("OPTIMAL FANTASY LINEUP")
        report.append("=" * 70)
        report.append("")
        
        # Budget summary
        report.append(f"Total Cost: ${total_cost:.2f}M / ${self.constraints.max_budget:.2f}M")
        report.append(f"Budget Used: {(total_cost/self.constraints.max_budget)*100:.1f}%")
        report.append(f"Over Base Budget: ${max(0, total_cost - self.constraints.base_budget):.2f}M")
        report.append("")
        
        # Fantasy Points summary
        report.append(f"Raw Fantasy Points: {raw_fantasy_points:.1f}")
        if penalty > 0:
            report.append(f"Budget Penalty: {penalty*100:.1f}% (-{penalty_fp:.1f} points)")
        effective_fp = raw_fantasy_points * (1 - penalty)
        report.append(f"Effective Fantasy Points: {effective_fp:.1f}")
        report.append("")
        
        # Value summary
        report.append(f"Total Value Score: {raw_value:.2f}")
        report.append(f"Average Value per Player: {raw_value/len(lineup):.2f}")
        report.append("")
        report.append("NOTE: Value score = fantasy_points / price")
        report.append("      Higher value = more fantasy points per dollar spent")
        report.append("")
        
        # Lineup by position
        grouped = self.group_players_by_position(lineup)
        
        for position in ['G', 'D', 'F']:
            position_name = {'G': 'GOALKEEPERS', 'D': 'DEFENDERS', 'F': 'FORWARDS'}[position]
            report.append(f"\n{position_name}:")
            report.append("-" * 70)
            
            pos_players = sorted(
                grouped[position],
                key=lambda p: p.get('fantasy_points', 0),
                reverse=True
            )
            
            for player in pos_players:
                name = player.get('name', 'Unknown')
                team = player.get('team', '???')
                cost = player.get('cena', player.get('price', 0))
                fp = player.get('fantasy_points', 0)
                value = player.get('value_score', 0)
                
                # Show key stats for context
                stats = player.get('stats', {})
                if position == 'G':
                    wins = int(stats.get('wins', stats.get('w', 0)))
                    saves = int(stats.get('saves', stats.get('sv', 0)))
                    stat_str = f"{wins}W {saves}SV"
                else:
                    goals = int(stats.get('goals', stats.get('g', 0)))
                    assists = int(stats.get('assists', stats.get('a', 0)))
                    stat_str = f"{goals}G {assists}A"
                
                report.append(
                    f"  {name:30s} {team:4s} | "
                    f"${cost:5.2f}M | FP: {fp:6.1f} | Value: {value:5.2f} | "
                    f"{stat_str}"
                )
        
        report.append("")
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def export_rankings(
        self,
        players: List[Dict],
        output_format: str = 'text'
    ) -> str:
        """
        Exports ranked player list in various formats.
        
        Args:
            players: List of all players with calculated values
            output_format: 'text', 'csv', or 'markdown'
            
        Returns:
            Formatted rankings as string
        """
        ranked = self.rank_players_by_value(players)
        
        if output_format == 'csv':
            lines = ["Rank,Name,Position,Team,Price,Projected Points,Value per Cost"]
            for i, player in enumerate(ranked, 1):
                lines.append(
                    f"{i},{player.get('name', 'Unknown')},"
                    f"{player.get('position', '?')},"
                    f"{player.get('team', '???')},"
                    f"{player.get('cena', 0):.2f},"
                    f"{player.get('projected_points', 0):.2f},"
                    f"{player.get('value_per_cost', 0):.3f}"
                )
            return "\n".join(lines)
        
        elif output_format == 'markdown':
            lines = ["# NHL Fantasy Player Rankings", ""]
            lines.append("| Rank | Name | Pos | Team | Price | Proj Pts | Value |")
            lines.append("|------|------|-----|------|-------|----------|-------|")
            
            for i, player in enumerate(ranked, 1):
                lines.append(
                    f"| {i} | {player.get('name', 'Unknown')} | "
                    f"{player.get('position', '?')} | "
                    f"{player.get('team', '???')} | "
                    f"${player.get('cena', 0):.2f}M | "
                    f"{player.get('projected_points', 0):.1f} | "
                    f"{player.get('value_per_cost', 0):.2f} |"
                )
            return "\n".join(lines)
        
        else:  # text format
            lines = ["=" * 80]
            lines.append("NHL FANTASY PLAYER RANKINGS")
            lines.append("=" * 80)
            lines.append("")
            lines.append(
                f"{'Rank':<6} {'Name':<25} {'Pos':<4} {'Team':<5} "
                f"{'Price':<8} {'Pts':<8} {'Value':<8}"
            )
            lines.append("-" * 80)
            
            for i, player in enumerate(ranked, 1):
                lines.append(
                    f"{i:<6} {player.get('name', 'Unknown'):<25} "
                    f"{player.get('position', '?'):<4} "
                    f"{player.get('team', '???'):<5} "
                    f"${player.get('cena', 0):>5.2f}M  "
                    f"{player.get('projected_points', 0):>6.1f}  "
                    f"{player.get('value_per_cost', 0):>6.2f}"
                )
            
            lines.append("")
            lines.append("=" * 80)
            return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    # Example player data
    example_players = [
        {
            'name': 'Connor McDavid',
            'position': 'C',
            'team': 'EDM',
            'cena': 12.5,
            'projected_points': 450
        },
        {
            'name': 'Auston Matthews',
            'position': 'C',
            'team': 'TOR',
            'cena': 11.8,
            'projected_points': 420
        },
        {
            'name': 'Cale Makar',
            'position': 'D',
            'team': 'COL',
            'cena': 10.2,
            'projected_points': 380
        }
    ]
    
    optimizer = LineupOptimizer()
    lineup, cost, points = optimizer.build_greedy_lineup(example_players)
    print(optimizer.generate_lineup_report(lineup, cost, points))