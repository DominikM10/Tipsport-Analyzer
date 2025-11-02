"""
Test and visualize the dynamic weighting and rookie amplification curves
"""
import math

def calculate_sigmoid_weight(games_played):
    """Calculate season weight using sigmoid function"""
    if games_played <= 0:
        return 0.15, 0.85
    
    L = 0.92
    k = 0.08
    x0 = 35
    
    games_capped = min(games_played, 82)
    current_weight = L / (1 + math.exp(-k * (games_capped - x0)))
    current_weight = max(0.15, current_weight)
    previous_weight = 1.0 - current_weight
    
    return current_weight, previous_weight

def calculate_rookie_amplification(games_played):
    """Calculate rookie amplification using exponential decay"""
    if games_played <= 0:
        return 1.40
    
    decay_rate = 20
    amplification = 1.05 + 0.30 * math.exp(-games_played / decay_rate)
    return amplification

def main():
    print("=" * 80)
    print("DYNAMIC SEASON WEIGHTING (Sigmoid Curve)")
    print("=" * 80)
    print(f"{'Games':<10} {'Current %':<15} {'Previous %':<15} {'Transition'}")
    print("-" * 80)
    
    test_games = [0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 82]
    
    for games in test_games:
        curr, prev = calculate_sigmoid_weight(games)
        
        # Visual bar
        curr_bars = int(curr * 40)
        prev_bars = int(prev * 40)
        visual = '█' * curr_bars + '░' * prev_bars
        
        print(f"{games:<10} {curr*100:>5.1f}% {'':<8} {prev*100:>5.1f}% {'':<8} {visual}")
    
    print("\n" + "=" * 80)
    print("ROOKIE AMPLIFICATION (Exponential Decay)")
    print("=" * 80)
    print(f"{'Games':<10} {'Amplification':<15} {'Boost %':<15} {'Visualization'}")
    print("-" * 80)
    
    for games in test_games:
        amp = calculate_rookie_amplification(games)
        boost_pct = (amp - 1.0) * 100
        
        # Visual bar (scale: 1.0 = 0 bars, 1.40 = 40 bars)
        bars = int((amp - 1.0) / 0.40 * 40)
        visual = '█' * bars
        
        print(f"{games:<10} {amp:>5.3f}x {'':<8} +{boost_pct:>5.1f}% {'':<8} {visual}")
    
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    print("\nSeason Weighting:")
    print("  • Uses sigmoid (S-curve) for smooth, natural transition")
    print("  • Rapid shift in mid-season (games 25-45) when sample becomes reliable")
    print("  • Gentle approach to max weight (92%) prevents overreaction to late-season slumps")
    print("  • Inflection point at game 35 (mid-season) for balanced transition")
    
    print("\nRookie Amplification:")
    print("  • Exponential decay reflects growing confidence in sample size")
    print("  • High boost early (1.35x) accounts for small sample variance")
    print("  • Drops rapidly in first 20 games as patterns emerge")
    print("  • Asymptotically approaches 1.05x (minimal boost) by season end")
    print("  • Prevents both undervaluing rookies AND overvaluing flukes")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
