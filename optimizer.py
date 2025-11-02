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
    
    # Lineup structure: 6 starters (3F + 2D + 1G) + 6 substitutes (3F + 2D + 1G)
    required_positions: Dict[str, int] = None
    substitute_positions: Dict[str, int] = None
    
    def __post_init__(self):
        if self.required_positions is None:
            self.required_positions = {
                'G': 1,   # 1 Goalkeeper
                'D': 2,   # 2 Defenders
                'F': 3    # 3 Forwards
            }
        if self.substitute_positions is None:
            self.substitute_positions = {
                'G': 1,   # 1 Substitute Goalkeeper
                'D': 2,   # 2 Substitute Defenders
                'F': 3    # 3 Substitute Forwards
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
        Optimizes for maximum effective fantasy points after budget penalties.
        
        Args:
            players: List of all available players with stats and prices
            max_budget: Target budget to stay close to (defaults to base budget + 10%)
            
        Returns:
            Tuple of (lineup, total_cost, effective_fantasy_points)
        """
        if max_budget is None:
            # Use base budget + 10% as target to minimize penalties
            max_budget = self.constraints.base_budget * 1.1
            
        # Filter out players with no price or name
        # Allow value_score >= 0 to include goalies with 0 fantasy points (early season, backup goalies)
        valid_players = [
            p for p in players 
            if p.get('value_score', 0) >= 0  # Allow 0 for goalies without stats yet
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
            # Rank by value_per_cost (fantasy points per dollar spent)
            grouped[pos] = self.rank_players_by_value(grouped[pos], 'value_per_cost')
            
            # Print top players in each position
            if grouped[pos]:
                print(f"\nTop 3 {pos} players by value:")
                for i, p in enumerate(grouped[pos][:3], 1):
                    print(f"  {i}. {p.get('name')} - {p.get('projected_points', 0):.1f} pts @ ${p.get('cena', 0):.1f}M = {p.get('value_per_cost', 0):.2f} pts/$M")
        
        starters = []
        substitutes = []
        total_cost = 0.0
        total_value = 0.0
        
        print("\n=== Selecting STARTERS (Best value players) ===")
        
        # Fill starter positions greedily (best value)
        for position, count in self.constraints.required_positions.items():
            available = grouped[position]
            selected_count = 0
            
            if len(available) < count:
                print(f"⚠️  Warning: Only {len(available)} {position} players available, need {count}")
            elif len(available) == count:
                print(f"ℹ️  Note: Exactly {count} {position} player(s) available - no alternatives for optimization")
            
            for player in available:
                if selected_count >= count:
                    break
                
                cost = player.get('cena', 0)
                value = player.get('value_score', 0)
                value_per_cost = player.get('value_per_cost', 0)
                proj_points = player.get('projected_points', 0)
                
                # Skip invalid players
                if cost <= 0 or value <= 0:
                    continue
                
                # Check if we can afford this player
                if total_cost + cost <= max_budget:
                    player['lineup_role'] = 'STARTER'
                    starters.append(player)
                    total_cost += cost
                    total_value += value
                    selected_count += 1
                    
                    # Add note if this is the only option and has poor value
                    reason = ""
                    if len(available) == 1 and value_per_cost < 5.0:
                        reason = " [ONLY OPTION AVAILABLE]"
                    elif len(available) == selected_count and value_per_cost < 5.0:
                        reason = " [REQUIRED TO FILL POSITION]"
                    
                    print(f"  ✓ {player.get('name')} ({position}) - {proj_points:.1f} pts @ ${cost:.1f}M = {value_per_cost:.2f} pts/$M{reason}")
                else:
                    # Try to find a cheaper alternative
                    cheaper_found = False
                    for alt_player in available[available.index(player)+1:]:
                        alt_cost = alt_player.get('cena', 0)
                        alt_value = alt_player.get('value_score', 0)
                        
                        if alt_cost > 0 and alt_value > 0 and total_cost + alt_cost <= max_budget:
                            alt_player['lineup_role'] = 'STARTER'
                            starters.append(alt_player)
                            total_cost += alt_cost
                            total_value += alt_value
                            selected_count += 1
                            alt_points = alt_player.get('projected_points', 0)
                            alt_vpc = alt_player.get('value_per_cost', 0)
                            print(f"  ✓ {alt_player.get('name')} ({position}) - {alt_points:.1f} pts @ ${alt_cost:.1f}M = {alt_vpc:.2f} pts/$M [budget pick]")
                            cheaper_found = True
                            break
                    
                    if not cheaper_found and selected_count < count:
                        print(f"  ⚠️  Could not afford {position} position #{selected_count + 1}")
            
            if selected_count < count:
                print(f"⚠️  Warning: Only selected {selected_count}/{count} {position} starters")
        
        print(f"\n✓ Starters complete: {len(starters)} players, ${total_cost:.2f}M")
        
        # OPTIMIZATION PHASE: Try swaps to maximize total effective fantasy points
        # This only affects STARTERS - substitutes selected afterwards independently
        print(f"\n🔄 Optimizing starter lineup (testing player swaps)...")
        
        # Remove selected starters from grouped for optimization
        starter_ids = {id(p) for p in starters}
        grouped_for_opt = {}
        for pos in grouped:
            grouped_for_opt[pos] = [p for p in grouped[pos] if id(p) not in starter_ids]
        
        starters, total_cost, effective_fp = self._optimize_lineup_swaps(
            starters, grouped_for_opt, max_budget, 
            initial_fp=sum(p.get('total_fantasy_points', 0) for p in starters) * (1 - self.calculate_budget_penalty(total_cost))
        )
        
        print(f"\n✓ Optimized starters: {len(starters)} players, ${total_cost:.2f}M, {effective_fp:.1f} effective FP")
        
        # NOW select substitutes - these are INDEPENDENT and don't affect total cost
        # Substitutes must be cheaper than the starter they would replace, but have best fantasy points among cheaper options
        
        print("\n=== Selecting SUBSTITUTES (Best cheaper alternatives for each starter) ===")
        
        # Group starters by position
        starters_by_pos = {'G': [], 'D': [], 'F': []}
        for player in starters:
            pos = self.normalize_position(player.get('position', ''))
            starters_by_pos[pos].append(player)
        
        # Track already used players (starters + already selected substitutes)
        used_player_keys = {(p.get('name'), p.get('team')) for p in starters}
        
        # For each position, find the best substitutes
        for position, count in self.constraints.substitute_positions.items():
            position_starters = starters_by_pos[position]
            selected_count = 0
            
            if not position_starters:
                print(f"⚠️  No {position} starters to find substitutes for")
                continue
            
            # Sort starters by cost (most expensive first) to find substitutes in priority order
            sorted_position_starters = sorted(position_starters, key=lambda p: p.get('cena', 0), reverse=True)
            
            # For each substitute slot, find the best cheaper alternative
            for i in range(count):
                if i >= len(sorted_position_starters):
                    # If we have more sub slots than starters, find additional cheaper options
                    # Use the cheapest starter as the max cost reference
                    reference_starter = min(position_starters, key=lambda p: p.get('cena', 0))
                else:
                    # Find substitute for the i-th most expensive starter
                    reference_starter = sorted_position_starters[i]
                
                max_cost = reference_starter.get('cena', 0)
                
                # Find all available players cheaper than this starter
                available = grouped[position]
                
                cheaper_alternatives = [
                    p for p in available 
                    if (p.get('name'), p.get('team')) not in used_player_keys  # Not already used
                    and p.get('cena', 0) < max_cost  # Cheaper than starter
                    and p.get('cena', 0) > 0  # Valid price
                    and p.get('total_fantasy_points', 0) > 0  # Has fantasy points
                ]
                
                if not cheaper_alternatives:
                    print(f"  ⚠️  No cheaper alternatives found for {reference_starter.get('name')} (${max_cost:.1f}M)")
                    continue
                
                # Select the one with HIGHEST fantasy points (best value among cheaper options)
                best_sub = max(cheaper_alternatives, key=lambda p: p.get('total_fantasy_points', 0))
                best_sub['lineup_role'] = 'SUBSTITUTE'
                best_sub['replaces'] = reference_starter.get('name')
                substitutes.append(best_sub)
                
                # Mark as used so we don't select again
                used_player_keys.add((best_sub.get('name'), best_sub.get('team')))
                
                cost = best_sub.get('cena', 0)
                proj_points = best_sub.get('total_fantasy_points', 0)
                savings = max_cost - cost
                
                print(f"  ✓ {best_sub.get('name')} ({position}) - {proj_points:.1f} pts @ ${cost:.1f}M (saves ${savings:.1f}M vs {reference_starter.get('name')})")
                selected_count += 1
            
            if selected_count < count:
                print(f"⚠️  Warning: Only selected {selected_count}/{count} {position} substitutes")
        
        # Combine starters and substitutes for reporting (but subs don't affect cost/optimization)
        lineup = starters + substitutes
        
        # Note: total_cost and effective_fp are already calculated from starters only
        print(f"\n✅ Final lineup: {len(starters)} starters + {len(substitutes)} substitutes = {len(lineup)} total")
        print(f"   Starter cost: ${total_cost:.2f}M (substitutes are independent)")
        print(f"   Effective Fantasy Points: {effective_fp:.1f} (from starters only)")
        
        return lineup, total_cost, effective_fp
    
    def _optimize_lineup_swaps(
        self,
        lineup: List[Dict],
        available_grouped: Dict[str, List[Dict]],
        max_budget: float,
        initial_fp: float,
        max_iterations: int = 100
    ) -> Tuple[List[Dict], float, float]:
        """
        Optimize lineup by trying player swaps to maximize total effective fantasy points.
        This fixes the greedy algorithm's limitation of only considering individual value ratios.
        
        Strategy:
        1. Try swapping each player with alternatives from their position
        2. Accept swap if it increases total effective fantasy points
        3. Consider budget impact - sometimes a cheaper player + budget headroom = better total
        
        Args:
            lineup: Current lineup
            available_grouped: Available players grouped by position
            max_budget: Maximum budget constraint
            initial_fp: Initial effective fantasy points
            max_iterations: Maximum swap attempts
            
        Returns:
            Optimized (lineup, total_cost, effective_fantasy_points)
        """
        best_lineup = lineup.copy()
        best_cost = sum(p.get('cena', 0) for p in best_lineup)
        best_fp = initial_fp
        improvements = 0
        
        # Build list of all available players (not in current lineup)
        lineup_ids = {(p.get('name'), p.get('team')) for p in lineup}
        
        for iteration in range(max_iterations):
            improved = False
            
            # Try swapping each player in the lineup
            for i, current_player in enumerate(best_lineup):
                current_pos = self.normalize_position(current_player.get('position', ''))
                current_cost = current_player.get('cena', 0)
                current_role = current_player.get('lineup_role', 'STARTER')
                
                # Get alternative players from same position (not in lineup)
                alternatives = [
                    p for p in available_grouped.get(current_pos, [])
                    if (p.get('name'), p.get('team')) not in lineup_ids
                ]
                
                # Try each alternative
                for alt_player in alternatives[:20]:  # Limit to top 20 for speed
                    alt_cost = alt_player.get('cena', 0)
                    
                    # Calculate new lineup cost
                    new_cost = best_cost - current_cost + alt_cost
                    
                    # Skip if over max budget
                    if new_cost > max_budget * 1.15:  # Allow 15% over for exploration
                        continue
                    
                    # Create test lineup with swap
                    test_lineup = best_lineup.copy()
                    test_lineup[i] = alt_player.copy()
                    test_lineup[i]['lineup_role'] = current_role  # Preserve role
                    
                    # Calculate new effective fantasy points
                    test_raw_fp = sum(p.get('total_fantasy_points', 0) for p in test_lineup)
                    test_penalty = self.calculate_budget_penalty(new_cost)
                    test_effective_fp = test_raw_fp * (1 - test_penalty)
                    
                    # Accept if improvement found
                    if test_effective_fp > best_fp:
                        print(f"  ✓ Swap: {current_player.get('name')} → {alt_player.get('name')} "
                              f"({current_pos}, ${current_cost:.1f}M → ${alt_cost:.1f}M) "
                              f"= +{test_effective_fp - best_fp:.1f} pts")
                        
                        # Update best lineup
                        lineup_ids.remove((current_player.get('name'), current_player.get('team')))
                        lineup_ids.add((alt_player.get('name'), alt_player.get('team')))
                        
                        best_lineup = test_lineup
                        best_cost = new_cost
                        best_fp = test_effective_fp
                        improvements += 1
                        improved = True
                        break
                
                if improved:
                    break  # Start over from first player after improvement
            
            # If no improvements in this iteration, we're done
            if not improved:
                break
        
        if improvements > 0:
            print(f"\n✅ Optimization complete: {improvements} improvements made")
            print(f"  Final Effective Fantasy Points: {best_fp:.1f} (+{best_fp - initial_fp:.1f})")
        else:
            print(f"\n✅ No improvements found - lineup already optimal")
        
        return best_lineup, best_cost, best_fp
    
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
        """
        # Separate starters and substitutes first
        starters = [p for p in lineup if p.get('lineup_role') == 'STARTER']
        substitutes = [p for p in lineup if p.get('lineup_role') == 'SUBSTITUTE']
        
        # Calculate stats from STARTERS only (substitutes are independent)
        starter_base_fp = sum(p.get('fantasy_points', 0) for p in starters)
        starter_bonus = sum(p.get('correlation_bonus', 0) for p in starters)
        starter_total_fp = sum(p.get('total_fantasy_points', 0) for p in starters)
        starter_value = sum(p.get('value_score', 0) for p in starters)
        penalty = self.calculate_budget_penalty(total_cost)
        penalty_fp = starter_total_fp * penalty
        
        report = []
        report.append("=" * 80)
        report.append("OPTIMAL FANTASY LINEUP")
        report.append("=" * 80)
        report.append("")
        
        # Budget summary (starters only)
        report.append(f"Starter Cost: ${total_cost:.2f}M / ${self.constraints.max_budget:.2f}M")
        report.append(f"Budget Used: {(total_cost/self.constraints.max_budget)*100:.1f}%")
        report.append(f"Over Base Budget: ${max(0, total_cost - self.constraints.base_budget):.2f}M")
        report.append("")
        
        # Fantasy Points summary (starters only)
        report.append(f"Starter Base Fantasy Points: {starter_base_fp:.1f}")
        report.append(f"Correlation Bonuses: +{starter_bonus:.1f}")
        report.append(f"Total Starter Fantasy Points: {starter_total_fp:.1f}")
        if penalty > 0:
            report.append(f"Budget Penalty: {penalty*100:.1f}% (-{penalty_fp:.1f} points)")
        effective_fp = starter_total_fp * (1 - penalty)
        report.append(f"Effective Fantasy Points: {effective_fp:.1f}")
        report.append("")
        
        # Value summary (starters only)
        report.append(f"Total Starter Value Score: {starter_value:.2f}")
        report.append(f"Average Value per Starter: {starter_value/len(starters) if starters else 0:.2f}")
        report.append("")
        report.append("NOTE: Cost and fantasy points only count starters")
        report.append("      Substitutes are independent alternatives (not added to total)")
        report.append("      Value score = total_fantasy_points / price")
        report.append("      Correlation bonuses (0-2) added based on unmapped stats")
        report.append("")
        
        # Find captain (player with highest total fantasy points among starters)
        captain = max(starters, key=lambda p: p.get('total_fantasy_points', 0)) if starters else None
        
        # STARTERS Section
        report.append("=" * 80)
        report.append("STARTERS (6 players)")
        report.append("=" * 80)
        report.append("")
        report.append("⭐ CAPTAIN: The player with the highest projected fantasy points")
        report.append("")
        
        grouped_starters = self.group_players_by_position(starters)
        
        for position in ['G', 'D', 'F']:
            position_name = {'G': 'GOALKEEPER', 'D': 'DEFENDERS', 'F': 'FORWARDS'}[position]
            report.append(f"\n{position_name}:")
            report.append("-" * 80)
            
            pos_players = sorted(
                grouped_starters[position],
                key=lambda p: p.get('total_fantasy_points', 0),
                reverse=True
            )
            
            for player in pos_players:
                name = player.get('name', 'Unknown')
                team = player.get('team', '???')
                cost = player.get('cena', player.get('price', 0))
                base_fp = player.get('fantasy_points', 0)
                bonus = player.get('correlation_bonus', 0)
                total_fp = player.get('total_fantasy_points', 0)
                value = player.get('value_score', 0)
                
                # Mark captain with special emoji
                captain_mark = " ⭐ CAPTAIN" if captain and player.get('id') == captain.get('id') else ""
                
                report.append(f"  {name} ({team}){captain_mark}")
                report.append(f"    Cost: ${cost:.2f}M | Fantasy Points: {base_fp:.1f} + {bonus:.1f} = {total_fp:.1f} | Value: {value:.2f}")
        
        # SUBSTITUTES Section
        report.append("")
        report.append("=" * 80)
        report.append("SUBSTITUTES (6 players)")
        report.append("=" * 80)
        
        grouped_subs = self.group_players_by_position(substitutes)
        
        for position in ['G', 'D', 'F']:
            position_name = {'G': 'GOALKEEPER', 'D': 'DEFENDERS', 'F': 'FORWARDS'}[position]
            report.append(f"\n{position_name}:")
            report.append("-" * 80)
            
            pos_players = sorted(
                grouped_subs[position],
                key=lambda p: p.get('total_fantasy_points', 0),
                reverse=True
            )
            
            for player in pos_players:
                name = player.get('name', 'Unknown')
                team = player.get('team', '???')
                cost = player.get('cena', player.get('price', 0))
                base_fp = player.get('fantasy_points', 0)
                bonus = player.get('correlation_bonus', 0)
                total_fp = player.get('total_fantasy_points', 0)
                value = player.get('value_score', 0)
                replaces = player.get('replaces', 'N/A')
                
                # Show key stats
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
                    f"  {name:30s} {team:4s} | ${cost:5.2f}M | "
                    f"FP: {base_fp:5.1f}+{bonus:3.1f}={total_fp:5.1f} | "
                    f"Val: {value:5.2f} | {stat_str} | [Alt for: {replaces}]"
                )
        
        report.append("")
        report.append("=" * 80)
        
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