"""Debug the dynamic weighting for Strome"""
import math

# Strome's current season games
games_played = 11

# Sigmoid parameters
L = 0.92
k = 0.08
x0 = 35

# Sigmoid function
games_capped = min(games_played, 82)
current_weight = L / (1 + math.exp(-k * (games_capped - x0)))
current_weight = max(0.15, current_weight)
previous_weight = 1.0 - current_weight

print("="*80)
print("DYNAMIC WEIGHTING DEBUG")
print("="*80)
print(f"\nGames played: {games_played}")
print(f"Current weight: {current_weight:.4f} ({current_weight*100:.2f}%)")
print(f"Previous weight: {previous_weight:.4f} ({previous_weight*100:.2f}%)")

# Now test with actual stats
current_goals = 5
previous_goals = 33

combined_goals = (current_goals * current_weight) + (previous_goals * previous_weight)
print(f"\nCurrent season goals: {current_goals}")
print(f"Previous season goals: {previous_goals}")
print(f"Combined (weighted): {combined_goals:.1f}")

# This should be much lower!
print(f"\nExpected: Should be close to current season prorated to full season")
print(f"Current pace: {current_goals} in {games_played} games = {(current_goals/games_played)*82:.1f} over 82 games")
