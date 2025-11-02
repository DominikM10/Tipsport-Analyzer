# Fantasy Points Calculation & Optimizer Improvements

## Issues Fixed

### 1. Fantasy Points Calculation (Initial Fix)
**Problem:** The optimizer was unable to generate optimal lineups because all players had 0 fantasy points and 0 value scores.

**Root Cause:** When player data was fetched from the NHL API in `main.py`, the code was only extracting a simplified stats dictionary, but the scoring system expected the complete data structure.

**Solution:** Modified the data loading process to preserve `featuredStats`, `seasonTotals`, and `careerTotals` structures from the NHL API.

### 2. Season Weighting (User Request)
**Problem:** Fantasy points were too high (e.g., 1140 points for Barkov) due to 80/20 weighting between current and previous seasons.

**Solution:** Changed weighting to **70% current season (2025-26)**, **30% previous season (2024-25)** in `scoring.py`

### 3. Value-Based Selection (User Request)
**Problem:** Optimizer wasn't clearly using "value per dollar" (points per $M) for selection.

**Solution:** Modified `optimizer.py` to:
- Sort players by `value_per_cost` (fantasy points per dollar)
- Show clear "pts/$M" metrics in selection output
- Display which players are selected based on best value

### 4. Budget Penalty Issues (User Request)
**Problem:** Lineups had 44.6% budget penalties, indicating optimizer went too far over budget (144.6M vs 100M base).

**Solution:** Changed optimizer default budget from unlimited to **base_budget + 10%** (110M) to minimize penalties:
- Base budget: $100M (no penalty)
- Target budget: $110M (only 10% penalty = 10M × 1% = 10% total)
- This ensures optimizer maximizes effective fantasy points after penalties

### 5. Team Filtering Visibility (User Request)
**Problem:** Not clear when team filtering was applied or which teams were selected.

**Solution:** Added verbose output showing:
- Which teams are being filtered
- How many players before/after filtering
- Clear confirmation of team-based lineup creation

## Changes Made

**File: `scoring.py`**
- Changed season weighting from 80/20 to 70/30 (lines 206-208)

**File: `optimizer.py`**
- Changed default max_budget to base_budget * 1.1 (110M) instead of 200M
- Modified to sort by `value_per_cost` instead of `value_score`
- Updated output to show "pts @ $X.XM = Y.YY pts/$M" format
- Return effective fantasy points instead of effective value score
- Added budget penalty display in optimization output

**File: `main.py`**
- Added team filtering visibility (lines 261-267)
- Added season weighting info to output (line 536)
- Added budget constraint info before optimization (lines 639-643)
- Improved output formatting throughout

## How to Use Team Filtering

### Filter by specific teams:
```bash
python main.py --source api --prices hraci_ceny.csv --teams TOR,MTL,BOS
```

### Filter by teams playing today:
```bash
python main.py --source api --prices hraci_ceny.csv --gameday today
```

### Filter by teams playing on a specific date:
```bash
python main.py --source api --prices hraci_ceny.csv --gameday 2025-11-15
```

## Result
✅ Fantasy points now use 70/30 season weighting (more current-season focused)
✅ Optimizer selects players by highest value per dollar (pts/$M)
✅ Budget penalties minimized (targets 110M vs unlimited)
✅ Team filtering works and is clearly visible in output
✅ All metrics and selections clearly displayed during optimization
