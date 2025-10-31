"""
Advanced NHL Fantasy Lineup Optimizer
Uses non-linear optimization with GameScore projections and regression analysis.
"""

import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Optional
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


class AdvancedLineupOptimizer:
    """
    Advanced optimizer using GameScore projections and non-linear optimization.
    """
    
    def __init__(self, base_budget: float = 100.0, max_budget: float = 120.0):
        """
        Initialize optimizer with budget constraints.
        
        Args:
            base_budget: Base budget before penalties apply (in millions)
            max_budget: Maximum allowable budget (in millions)
        """
        self.base_budget = base_budget
        self.max_budget = max_budget
        self.penalty_rate = 0.01  # 1% per million over base
        
        # For position requirements (12 players: 2G + 4D + 6F)
        self.position_requirements = {
            'G': 2,
            'D': 4,
            'F': 6
        }
        self.total_players = sum(self.position_requirements.values())
    
    def prepare_player_dataframe(self, players: List[Dict]) -> pd.DataFrame:
        """
        Convert player list to pandas DataFrame with all necessary calculations.
        
        Args:
            players: List of player dictionaries
            
        Returns:
            DataFrame with calculated metrics
        """
        from scoring import FantasyScorer
        
        scorer = FantasyScorer()
        
        # Extract relevant data
        data = []
        for player in players:
            # Skip players without price
            price = player.get('cena', 0)
            if price <= 0:
                continue
            
            # Calculate metrics
            gs_per_game = scorer.calculate_game_score(player)
            fp_per_game = scorer.calculate_fantasy_points_per_game(player)
            
            # Get stats for additional context
            stats = scorer._extract_stats(player)
            games = scorer._get_stat(stats, 'games', 'gamesPlayed', 'games_played')
            
            if games == 0:
                continue
            
            data.append({
                'name': player.get('name', 'Unknown'),
                'position': scorer._normalize_position(player.get('position', 'F')),
                'team': player.get('team', '???'),
                'price': price,
                'games': games,
                'gs_per_game': gs_per_game,
                'fp_per_game': fp_per_game,
                'total_gs': gs_per_game * games,
                'total_fp': fp_per_game * games
            })
        
        df = pd.DataFrame(data)
        
        if len(df) == 0:
            return df
        
        # Calculate projected FP using regression
        df = self._calculate_projected_fp(df)
        
        return df
    
    def _calculate_projected_fp(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Use regression to project fantasy points from GameScore.
        
        Args:
            df: DataFrame with gs_per_game and fp_per_game
            
        Returns:
            DataFrame with projected_fp_per_game column added
        """
        # Filter out players with insufficient data
        valid_data = df[(df['gs_per_game'] > 0) & (df['fp_per_game'] > 0)].copy()
        
        if len(valid_data) < 10:
            # Not enough data for regression, use simple ratio
            print("⚠️  Insufficient data for regression, using simple ratio method")
            total_fp = df['total_fp'].sum()
            total_gs = df['total_gs'].sum()
            
            if total_gs > 0:
                fp_per_gs_ratio = total_fp / total_gs
                df['projected_fp_per_game'] = df['gs_per_game'] * fp_per_gs_ratio
            else:
                df['projected_fp_per_game'] = df['fp_per_game']
            
            return df
        
        # Prepare data for regression
        X = valid_data[['gs_per_game']].values
        y = valid_data['fp_per_game'].values
        
        # Fit linear regression
        model = LinearRegression()
        model.fit(X, y)
        
        # Calculate R² score
        r2_score = model.score(X, y)
        print(f"✓ Regression model R² score: {r2_score:.3f}")
        print(f"  Coefficient: {model.coef_[0]:.3f}, Intercept: {model.intercept_:.3f}")
        
        # Predict for all players
        df['projected_fp_per_game'] = model.predict(df[['gs_per_game']])
        
        # Ensure non-negative projections
        df['projected_fp_per_game'] = df['projected_fp_per_game'].clip(lower=0)
        
        # Calculate projected season total (assuming 82 games)
        df['projected_season_fp'] = df['projected_fp_per_game'] * 82
        
        return df
    
    def calculate_penalty(self, total_price: float) -> float:
        """Calculate budget penalty percentage."""
        if total_price <= self.base_budget:
            return 0.0
        
        overage = total_price - self.base_budget
        return overage * self.penalty_rate
    
    def objective_function(self, x: np.ndarray, df: pd.DataFrame) -> float:
        """
        Objective function to minimize (negative of net fantasy points).
        
        Args:
            x: Binary array indicating selected players
            df: DataFrame with player data
            
        Returns:
            Negative net fantasy points (for minimization)
        """
        # Convert to binary
        selected = x > 0.5
        
        if not np.any(selected):
            return 1e10  # Large penalty for empty selection
        
        selected_players = df[selected]
        
        # Calculate totals
        total_price = selected_players['price'].sum()
        total_projected_fp = selected_players['projected_season_fp'].sum()
        
        # Apply penalty
        penalty = self.calculate_penalty(total_price)
        net_fp = total_projected_fp * (1.0 - penalty)
        
        # Return negative for minimization
        return -net_fp
    
    def optimize_lineup(
        self,
        players: List[Dict],
        method: str = 'SLSQP',
        verbose: bool = True
    ) -> Tuple[List[Dict], float, float, pd.DataFrame]:
        """
        Optimize lineup using non-linear constrained optimization.
        
        Args:
            players: List of player dictionaries
            method: Optimization method ('SLSQP' or 'trust-constr')
            verbose: Whether to print progress
            
        Returns:
            Tuple of (lineup, total_cost, net_points, dataframe)
        """
        if verbose:
            print("\n🔬 Preparing advanced optimization...")
        
        # Prepare data
        df = self.prepare_player_dataframe(players)
        
        if len(df) == 0:
            print("❌ No valid players for optimization")
            return [], 0.0, 0.0, df
        
        if verbose:
            print(f"✓ Prepared {len(df)} players for optimization")
            print(f"  Average GS/G: {df['gs_per_game'].mean():.3f}")
            print(f"  Average projected FP/G: {df['projected_fp_per_game'].mean():.2f}")
        
        # Group by position
        position_groups = {pos: df[df['position'] == pos].index.tolist() 
                          for pos in ['G', 'D', 'F']}
        
        n_players = len(df)
        
        # Define constraints
        constraints = []
        
        # Total players = 12
        constraints.append({
            'type': 'eq',
            'fun': lambda x: np.sum(x) - self.total_players
        })
        
        # Position requirements
        for pos, required_count in self.position_requirements.items():
            indices = position_groups.get(pos, [])
            if not indices:
                print(f"⚠️  Warning: No {pos} players available!")
                continue
                
            def make_position_constraint(pos_indices, count):
                return lambda x: np.sum(x[pos_indices]) - count
            
            constraints.append({
                'type': 'eq',
                'fun': make_position_constraint(indices, required_count)
            })
        
        # Budget constraint (max budget)
        constraints.append({
            'type': 'ineq',
            'fun': lambda x: self.max_budget - np.sum(df.loc[x > 0.5, 'price'])
        })
        
        # Bounds: each variable between 0 and 1
        bounds = [(0, 1) for _ in range(n_players)]
        
        # Initial guess: select top players by projected value per cost
        df['value_per_cost'] = df['projected_season_fp'] / df['price']
        
        x0 = np.zeros(n_players)
        
        # Start with best value players from each position
        for pos, required_count in self.position_requirements.items():
            pos_df = df[df['position'] == pos].nlargest(required_count, 'value_per_cost')
            x0[pos_df.index] = 1.0
        
        if verbose:
            print(f"\n🎯 Running {method} optimization...")
            print(f"  Constraints: {len(constraints)}")
            print(f"  Variables: {n_players}")
        
        # Run optimization
        result = minimize(
            self.objective_function,
            x0,
            args=(df,),
            method=method,
            bounds=bounds,
            constraints=constraints,
            options={'disp': verbose, 'maxiter': 1000}
        )
        
        if not result.success:
            print(f"⚠️  Optimization warning: {result.message}")
        
        # Round to binary (select top 12 values closest to 1)
        x_binary = np.zeros(n_players)
        top_indices = np.argsort(result.x)[-self.total_players:]
        x_binary[top_indices] = 1
        
        # Verify position constraints
        selected_df = df[x_binary > 0.5].copy()
        
        # Check if we meet position requirements
        for pos, required_count in self.position_requirements.items():
            actual_count = len(selected_df[selected_df['position'] == pos])
            if actual_count != required_count:
                if verbose:
                    print(f"⚠️  Position constraint violation: {pos} has {actual_count}, need {required_count}")
                # Try to fix by swapping players
                selected_df = self._fix_position_constraints(df, selected_df)
        
        # Calculate final metrics
        total_cost = selected_df['price'].sum()
        total_projected = selected_df['projected_season_fp'].sum()
        penalty = self.calculate_penalty(total_cost)
        net_points = total_projected * (1.0 - penalty)
        
        # Convert back to player dictionaries
        lineup = []
        for idx, row in selected_df.iterrows():
            player_dict = {
                'name': row['name'],
                'position': row['position'],
                'team': row['team'],
                'cena': row['price'],
                'projected_points': row['projected_season_fp'],
                'gs_per_game': row['gs_per_game'],
                'fp_per_game': row['projected_fp_per_game'],
                'games': row['games']
            }
            lineup.append(player_dict)
        
        return lineup, total_cost, net_points, df
    
    def _fix_position_constraints(
        self,
        full_df: pd.DataFrame,
        selected_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Attempt to fix position constraint violations by swapping players.
        
        Args:
            full_df: Full player DataFrame
            selected_df: Currently selected players
            
        Returns:
            Fixed DataFrame
        """
        # Count current positions
        position_counts = selected_df['position'].value_counts().to_dict()
        
        for pos, required in self.position_requirements.items():
            current = position_counts.get(pos, 0)
            
            if current < required:
                # Need more of this position
                deficit = required - current
                available = full_df[(full_df['position'] == pos) & 
                                   (~full_df.index.isin(selected_df.index))]
                
                if len(available) >= deficit:
                    # Add best available
                    to_add = available.nlargest(deficit, 'value_per_cost')
                    selected_df = pd.concat([selected_df, to_add])
            
            elif current > required:
                # Have too many of this position
                excess = current - required
                pos_players = selected_df[selected_df['position'] == pos]
                # Remove worst performers
                to_remove = pos_players.nsmallest(excess, 'value_per_cost')
                selected_df = selected_df[~selected_df.index.isin(to_remove.index)]
        
        return selected_df
    
    def generate_report(
        self,
        lineup: List[Dict],
        total_cost: float,
        net_points: float,
        df: pd.DataFrame
    ) -> str:
        """Generate detailed optimization report."""
        lines = []
        lines.append("=" * 80)
        lines.append("ADVANCED OPTIMIZATION RESULTS")
        lines.append("=" * 80)
        lines.append("")
        
        # Calculate metrics
        total_projected = sum(p['projected_points'] for p in lineup)
        penalty = self.calculate_penalty(total_cost)
        
        lines.append(f"Total Cost: ${total_cost:.2f}M")
        lines.append(f"Base Budget: ${self.base_budget:.2f}M")
        lines.append(f"Overage: ${max(0, total_cost - self.base_budget):.2f}M")
        lines.append(f"Penalty: {penalty*100:.2f}%")
        lines.append("")
        lines.append(f"Projected Season Points: {total_projected:.1f}")
        lines.append(f"Net Points (after penalty): {net_points:.1f}")
        lines.append("")
        
        # Lineup by position
        for pos in ['G', 'D', 'F']:
            pos_name = {'G': 'GOALKEEPERS', 'D': 'DEFENDERS', 'F': 'FORWARDS'}[pos]
            pos_players = [p for p in lineup if p['position'] == pos]
            
            lines.append(f"\n{pos_name}:")
            lines.append("-" * 80)
            
            for p in sorted(pos_players, key=lambda x: x['projected_points'], reverse=True):
                lines.append(
                    f"  {p['name']:30s} {p['team']:4s} | "
                    f"${p['cena']:5.2f}M | "
                    f"GS/G: {p['gs_per_game']:5.3f} | "
                    f"Proj: {p['projected_points']:6.1f}"
                )
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    print("Advanced optimizer module loaded successfully")
