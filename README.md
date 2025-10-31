# NHL Fantasy Lineup Optimizer

A comprehensive tool for optimizing NHL fantasy lineups based on player statistics, projections, and custom pricing.

## Features

- Fetch latest player data from the official NHL API
- Calculate fantasy point projections based on current and historical performance
- Import player prices from various file formats (CSV, JSON, text)
- Find optimal lineups within budget constraints
- Support for greedy, iterative, and advanced ML-based optimization methods
- Generate detailed reports and player rankings

## Requirements

- Python 3.7+
- Required libraries: `requests`, `difflib`, `numpy`, `scipy`, `pandas`, `scikit-learn`

## Installation

1. Clone the repository or download the source code
2. Install requirements: 
```bash
pip install requests numpy scipy pandas scikit-learn
```

## Usage

### Basic Usage

```bash
# Run analysis using API data with player prices from a CSV file
python main.py --source api --prices hraci_ceny.csv

# Run with CSV data source and CSV prices
python main.py --source csv --file player_data.csv --prices hraci_ceny.csv

# Run with Tipsport text input for players and CSV for prices
python main.py --source tipsport --file tipsport_export.txt --prices hraci_ceny.csv
```

### Advanced Usage

```bash
# Use advanced ML-based optimization with GameScore projections
python main.py --source api --prices hraci_ceny.csv --method advanced

# Filter by specific teams
python main.py --source api --prices hraci_ceny.csv --teams TOR,MTL,BOS

# Filter by teams playing on a specific date
python main.py --source api --prices hraci_ceny.csv --gameday 2024-01-15

# Use today's games
python main.py --source api --prices hraci_ceny.csv --gameday today
```

### Command Line Options

- `--source`: Data source type (`api`, `csv`, `json`, `tipsport`)
- `--file`: Path to input file for CSV/JSON/Tipsport sources
- `--prices`: Path to CSV file containing player prices
- `--method`: Optimization method (`greedy`, `iterative`, or `advanced`)
- `--output`: Directory for saving reports
- `--budget`: Custom budget limit in millions
- `--refresh`: Force refresh of cached API data
- `--clear-cache`: Clear all cached data and exit
- `--teams`: Comma-separated list of team abbreviations to filter
- `--gameday`: Date (YYYY-MM-DD) or "today" to filter teams by game day
- `--advanced`: Use advanced ML-based optimization (same as --method advanced)
- `--no-interactive`: Disable interactive prompts
- `--history`: Show lineup history

### Player Prices CSV Format

The player prices CSV file should be in one of these formats:

**Format 1: Split Decimal (Recommended)**
```csv
Makar C.,30,9
McDavid C.,21,9
Matthews A.,24,5
```

**Format 2: Single Price Column**
```csv
Makar C.,30.9
McDavid C.,21.9
Matthews A.,24.5
```

**Important:** Player names must be in the format: `LastName FirstInitial.`

## Optimization Methods

### Greedy (Default)
Fast method that selects best value players first. Good for quick results.

### Iterative
Tries multiple combinations and swaps to find better lineups. Slower but more thorough.

### Advanced
Uses machine learning with GameScore projections and regression analysis. Best for accurate predictions but requires more computation time.

## Data Flow

1. Fetch player data from NHL API or load from local file
2. Parse player prices from CSV file
3. Match players with their prices
4. Calculate fantasy points projections or value scores
5. Generate optimal lineup within budget constraints
6. Export lineup and player rankings

## Cache Management

The application caches API data to improve performance. To refresh the data:

```bash
# Force refresh during analysis
python main.py --source api --refresh --prices hraci_ceny.csv

# Clear all cached data
python main.py --clear-cache
```

## Examples

```bash
# Basic greedy optimization
python main.py --source api --prices hraci_ceny.csv

# Advanced optimization with team filter
python main.py --source api --prices hraci_ceny.csv --method advanced --teams TOR,EDM

# Iterative optimization for today's games
python main.py --source api --prices hraci_ceny.csv --method iterative --gameday today

# View lineup history
python main.py --history
```