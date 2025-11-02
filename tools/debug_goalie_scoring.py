"""Debug goalie scoring calculation"""
from scoring import FantasyScorer

scorer = FantasyScorer()

# Simulate Varlamov's stats
stats = {
    'gamesPlayed': 8,
    'wins': 3,
    'losses': 3,
    'shutouts': 0,
    'goalsAgainst': 21
}

print("="*80)
print("GOALIE SCORING DEBUG")
print("="*80)

print(f"\nInput stats: {stats}")
print(f"\nScoring rules:")
print(f"  games_played: {scorer.goalie_scoring.get('games_played')}")
print(f"  win: {scorer.goalie_scoring.get('win')}")
print(f"  loss: {scorer.goalie_scoring.get('loss')}")
print(f"  shutout: {scorer.goalie_scoring.get('shutout')}")
print(f"  goal_against: {scorer.goalie_scoring.get('goal_against')}")

# Manual calculation
games = stats['gamesPlayed']
wins = stats['wins']
losses = stats['losses']
shutouts = stats['shutouts']
ga = stats['goalsAgainst']

gp_points = games * scorer.goalie_scoring.get('games_played', 0)
win_points = wins * scorer.goalie_scoring.get('win', 0)
loss_points = losses * scorer.goalie_scoring.get('loss', 0)
so_points = shutouts * scorer.goalie_scoring.get('shutout', 0)
ga_points = ga * scorer.goalie_scoring.get('goal_against', 0)

print(f"\nManual calculation:")
print(f"  GP: {games} × {scorer.goalie_scoring.get('games_played', 0)} = {gp_points}")
print(f"  Wins: {wins} × {scorer.goalie_scoring.get('win', 0)} = {win_points}")
print(f"  Losses: {losses} × {scorer.goalie_scoring.get('loss', 0)} = {loss_points}")
print(f"  Shutouts: {shutouts} × {scorer.goalie_scoring.get('shutout', 0)} = {so_points}")
print(f"  Goals Against: {ga} × {scorer.goalie_scoring.get('goal_against', 0)} = {ga_points}")
print(f"  TOTAL: {gp_points + win_points + loss_points + so_points + ga_points}")

# Now test with the actual method
result = scorer._calculate_goalie_points(stats)
print(f"\nActual result from _calculate_goalie_points: {result}")
