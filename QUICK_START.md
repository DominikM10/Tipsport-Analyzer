# Quick Start Guide - NHL Fantasy Optimizer

## Basic Usage

### 1. Simple Optimization (All Teams)
```bash
python main.py --source api --prices hraci_ceny.csv
```
This will:
- Fetch all NHL players from the API
- Match them with prices from your CSV file
- Calculate fantasy points (70% current season, 30% previous)
- Create optimal lineup maximizing value per dollar
- Target budget: $110M (10% penalty)

### 2. Filter by Specific Teams
```bash
python main.py --source api --prices hraci_ceny.csv --teams TOR,BOS,MTL
```
This creates a lineup using ONLY players from Toronto, Boston, and Montreal.

### 3. Filter by Today's Games
```bash
python main.py --source api --prices hraci_ceny.csv --gameday today
```
This automatically finds teams playing today and creates a lineup from those players.

### 4. Filter by Specific Game Day
```bash
python main.py --source api --prices hraci_ceny.csv --gameday 2025-11-15
```
This finds teams playing on November 15, 2025 and creates a lineup from those players.

### 5. Advanced ML-Based Optimization
```bash
python main.py --source api --prices hraci_ceny.csv --method advanced
```
Uses machine learning with GameScore projections for more accurate predictions.

### 6. Custom Budget Target
```bash
python main.py --source api --prices hraci_ceny.csv --budget 120
```
Sets a custom budget target (default is 110M to minimize penalties).

## Understanding the Output

### Budget Information
```
Base budget: $100.0M (no penalty)
Penalty: 1.0% per $1M over base
Target budget: $110.0M
```
- **Base budget**: $100M with no penalty
- **Penalty**: 1% per million over $100M
- **Target**: Optimizer aims for $110M (10% total penalty)
- Going to $120M = 20% penalty, $144.6M = 44.6% penalty

### Player Selection
```
✓ Player Name (F) - 245.3 pts @ $15.2M = 16.14 pts/$M
```
- **245.3 pts**: Total fantasy points (includes bonuses)
- **$15.2M**: Player cost
- **16.14 pts/$M**: Value per dollar (higher is better)

### Fantasy Points Calculation
```
Season weighting: 70% current (2025-26), 30% previous (2024-25)
Base Fantasy Points: 1250.5
Correlation Bonuses: +45.2
Total Fantasy Points: 1295.7
Budget Penalty: 10.0% (-129.6 points)
Effective Fantasy Points: 1166.1
```
- **Base FP**: Points from goals, assists, shots, hits, etc.
- **Bonuses**: Additional points based on correlation with top performers
- **Total FP**: Base + Bonuses
- **Penalty**: Reduction for going over $100M budget
- **Effective FP**: What you actually get after penalty

## Optimization Strategies

### Strategy 1: Maximize Value (Default)
```bash
python main.py --source api --prices hraci_ceny.csv
```
- Selects players with highest pts/$M ratio
- Targets $110M budget
- Balances performance vs. cost

### Strategy 2: Premium Players (High Budget)
```bash
python main.py --source api --prices hraci_ceny.csv --budget 130
```
- Allows spending more on star players
- Higher penalty (30%) but may be worth it
- Good when top players have extreme value

### Strategy 3: Today's Games Only
```bash
python main.py --source api --prices hraci_ceny.csv --gameday today
```
- Only players in today's games
- Maximizes immediate value
- Good for daily fantasy contests

### Strategy 4: Specific Team Focus
```bash
python main.py --source api --prices hraci_ceny.csv --teams COL,EDM,TOR
```
- Only Colorado, Edmonton, Toronto players
- Good when you know these teams are hot
- Reduces player pool for easier selection

ANA – Mighty Ducks of Anaheim/Anaheim Ducks
BOS – Boston Bruins
BUF – Buffalo Sabres
CAR – Carolina Hurricanes
CBJ – Columbus Blue Jackets
CGY – Calgary Flames
CHI – Chicago Black Hawks/Blackhawks
COL – Colorado Avalanche
DAL – Dallas Stars
DET – Detroit Red Wings
EDM – Edmonton Oilers
FLA – Florida Panthers
LAK – Los Angeles Kings
MIN – Minnesota Wild
MTL – Montreal Canadiens
NJD – New Jersey Devils
NSH – Nashville Predators
NYI – New York Islanders
NYR – New York Rangers
OTT – Ottawa Senators
PHI – Philadelphia Flyers
PIT – Pittsburgh Penguins
SEA – Seattle Kraken
SJS – San Jose Sharks
STL – St. Louis Blues
TBL – Tampa Bay Lightning
TOR – Toronto Maple Leafs
UTA – Utah Hockey Club/Utah Mammoth
VAN – Vancouver Canucks
VGK – Vegas Golden Knights
WPG – Winnipeg Jets
WSH – Washington Capitals


## Advanced Features

### Force Refresh API Data
```bash
python main.py --source api --prices hraci_ceny.csv --refresh
```
Clears cache and fetches fresh data from NHL API.

### Clear Cache
```bash
python main.py --clear-cache
```
Removes all cached player data.

### View Lineup History
```bash
python main.py --history
```
Shows your last 10 lineups.

### Non-Interactive Mode
```bash
python main.py --source api --prices hraci_ceny.csv --no-interactive
```
Skips all prompts (good for scripts/automation).

## Understanding Value Per Cost

The optimizer ranks players by **value per cost** (fantasy points per $1M spent):

**Example:**
- Player A: 300 pts @ $20M = **15.0 pts/$M**
- Player B: 250 pts @ $15M = **16.7 pts/$M** ← BETTER VALUE
- Player C: 400 pts @ $30M = **13.3 pts/$M**

Player B gives you the most "bang for your buck" even though Player C has more total points.

## Tips

1. **Start with default settings** to see what the optimizer recommends
2. **Check the budget penalty** - if it's over 20%, consider lowering budget target
3. **Use team filtering** when you know specific teams are playing or hot
4. **Compare multiple runs** using `--history` to see trends
5. **Refresh data daily** with `--refresh` for most accurate projections
6. **Look at value per cost** (pts/$M) - higher is always better
7. **Don't overspend** - a $144M lineup with 44.6% penalty loses 346 points vs $110M!

## Common Issues

### "No players were matched with prices"
- Check your `hraci_ceny.csv` format (see PRICE_FILE_GUIDE.md)
- Player names must be: `LastName FirstInitial.` (e.g., `Crosby S.`)

### "Only X/12 players selected"
- Not enough players in selected teams/gameday
- Try expanding team filter or removing gameday restriction

### "Budget penalty is too high"
- Use `--budget 110` or lower
- Select cheaper players with better value per cost
- Check if prices in CSV are reasonable

## Output Files

After each run, these files are created:
- `optimal_lineup_TIMESTAMP.txt` - Formatted lineup report
- `player_rankings_TIMESTAMP.csv` - All players ranked by value
- `players_with_scores_TIMESTAMP.json` - Complete player data
- `lineup_history.json` - Last 10 lineups for comparison
