"""
Debug tool for NHL Fantasy Analyzer
This script helps diagnose data issues by analyzing player data and price files.
"""

import json
import csv
import os
import sys
from typing import Dict, List, Any, Optional
import difflib

def load_json_file(filepath: str) -> Any:
    """Load any JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file {filepath}: {e}")
        return None

def load_csv_file(filepath: str) -> List[Dict]:
    """Load a CSV file as list of dictionaries"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Error loading CSV file {filepath}: {e}")
        return []

def analyze_player_data(filepath: str) -> None:
    """Analyze a player data file"""
    print(f"Analyzing player data from {filepath}")
    
    data = load_json_file(filepath)
    if not data:
        return
        
    if isinstance(data, dict):
        # Handle dict format
        if 'players' in data:
            players = data['players']
        else:
            players = [data]
    elif isinstance(data, list):
        # Handle list format
        players = data
    else:
        print(f"Unknown data format: {type(data)}")
        return
    
    # Basic stats
    print(f"Total players: {len(players)}")
    
    # Check for prices
    players_with_price = [p for p in players if p.get('cena', 0) > 0]
    print(f"Players with prices: {len(players_with_price)}")
    
    # Check for points
    players_with_points = [p for p in players if p.get('projected_points', 0) > 0]
    print(f"Players with projected points: {len(players_with_points)}")
    
    # Check for both
    valid_players = [p for p in players if p.get('cena', 0) > 0 and p.get('projected_points', 0) > 0]
    print(f"Valid players (with price and points): {len(valid_players)}")
    
    # Check positions
    positions = {}
    for p in players:
        pos = p.get('position', 'Unknown')
        positions[pos] = positions.get(pos, 0) + 1
    print("Position counts:")
    for pos, count in positions.items():
        print(f"  {pos}: {count}")
    
    # Show sample valid players
    if valid_players:
        print("\nSample valid players:")
        for p in valid_players[:5]:
            name = p.get('name', 'Unknown')
            pos = p.get('position', '?')
            price = p.get('cena', 0)
            points = p.get('projected_points', 0)
            print(f"  {name} ({pos}) - ${price:.1f}M, {points:.1f} pts")
    
    # Show sample invalid players
    invalid_players = [p for p in players if p.get('cena', 0) == 0 or p.get('projected_points', 0) == 0]
    if invalid_players:
        print("\nSample invalid players:")
        for p in invalid_players[:5]:
            name = p.get('name', 'Unknown')
            pos = p.get('position', '?')
            price = p.get('cena', 0)
            points = p.get('projected_points', 0)
            print(f"  {name} ({pos}) - ${price:.1f}M, {points:.1f} pts")

def analyze_price_file(filepath: str) -> None:
    """Analyze a price file"""
    print(f"\nAnalyzing price file: {filepath}")
    
    if filepath.endswith('.csv'):
        # Try to parse as CSV
        prices = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                
                # Check for header
                first_row = next(reader, None)
                if first_row and any(h.lower() in ['hráč', 'player', 'name'] for h in first_row):
                    print(f"Header detected: {first_row}")
                else:
                    # Process as data row
                    name = first_row[0] if first_row else None
                    if name and len(first_row) >= 3:
                        price = float(f"{first_row[1]}.{first_row[2]}")
                        prices[name] = price
                
                # Process remaining rows
                for row in reader:
                    if row and len(row) >= 3:
                        name = row[0]
                        price = float(f"{row[1]}.{row[2]}")
                        prices[name] = price
            
            print(f"Found {len(prices)} prices in CSV format")
            print("Sample prices:")
            for name, price in list(prices.items())[:5]:
                print(f"  {name}: {price}M")
        except Exception as e:
            print(f"Error parsing CSV: {e}")
    else:
        # Try to load as JSON
        data = load_json_file(filepath)
        if isinstance(data, list):
            print(f"Found {len(data)} entries in JSON list format")
            print("Sample entries:")
            for entry in data[:5]:
                print(f"  {entry}")
        elif isinstance(data, dict):
            print(f"Found {len(data)} entries in JSON dict format")
            print("Sample entries:")
            for k, v in list(data.items())[:5]:
                print(f"  {k}: {v}")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python debug_data.py <file_to_analyze>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} does not exist")
        sys.exit(1)
    
    # Analyze based on file type
    if filepath.endswith('.json'):
        analyze_player_data(filepath)
    elif filepath.endswith('.csv') or filepath.endswith('.txt'):
        analyze_price_file(filepath)
    else:
        print(f"Unknown file type: {filepath}")

if __name__ == "__main__":
    main()
