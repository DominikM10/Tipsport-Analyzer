"""
Price Matching Debug Tool
Helps diagnose and fix issues with matching player names to price data.
"""

import json
import os
import sys
import csv
from typing import Dict, List
import difflib
import unicodedata
import re

def normalize_name(name: str) -> str:
    """Return a normalized name for comparison."""
    if not name:
        return ''
    # Normalize unicode, remove diacritics
    name = unicodedata.normalize('NFKD', name)
    name = ''.join(ch for ch in name if not unicodedata.combining(ch))
    # Lowercase, remove special chars, keep alphanumerics and spaces
    name = name.lower().replace('.', ' ').replace(',', ' ')
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def generate_name_variants(name: str) -> List[str]:
    """Generate multiple variants of a player name."""
    variants = set()
    
    # Original name
    variants.add(name.lower())
    
    # Normalize
    norm_name = normalize_name(name)
    if norm_name and norm_name != name.lower():
        variants.add(norm_name)
    
    # Split into tokens
    tokens = norm_name.split() if norm_name else []
    
    if len(tokens) >= 2:
        # Last name + first initial
        variants.add(f"{tokens[-1]} {tokens[0][0]}")
        
        # Last name only
        variants.add(tokens[-1])
        
        # Last name + first initial with period
        variants.add(f"{tokens[-1]} {tokens[0][0]}.")
    
    return list(filter(None, variants))

def load_price_data(filepath: str) -> List[Dict]:
    """Load price data from a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading price data: {e}")
        return []

def load_player_data(filepath: str) -> List[Dict]:
    """Load player data from a JSON or CSV file."""
    if filepath.lower().endswith('.json'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'players' in data:
                    return data['players']
                else:
                    return [data]
        except Exception as e:
            print(f"Error loading player data: {e}")
            return []
    elif filepath.lower().endswith('.csv'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            print(f"Error loading CSV data: {e}")
            return []
    else:
        print(f"Unsupported file format: {filepath}")
        return []

def analyze_price_matching(players: List[Dict], prices: List[Dict], output_file: str = None):
    """Analyze and debug price matching issues."""
    print(f"Analyzing price matching for {len(players)} players and {len(prices)} price entries")
    
    # Convert price list to dict for easier lookups
    price_dict = {p['name']: p['price'] for p in prices}
    
    # Normalize all price names for matching
    norm_prices = {}
    for name, price in price_dict.items():
        norm_name = normalize_name(name)
        if norm_name:
            norm_prices[norm_name] = price
    
    # Create list for storing match results
    results = []
    
    # Stats
    matched_count = 0
    
    # Process each player
    for player in players:
        player_name = player.get('name', player.get('fullName', ''))
        if not player_name:
            continue
        
        # Generate variants
        variants = generate_name_variants(player_name)
        
        # Check for matches
        match_found = False
        match_type = None
        match_price = None
        match_name = None
        
        # Direct match
        if player_name in price_dict:
            match_found = True
            match_type = "direct"
            match_price = price_dict[player_name]
            match_name = player_name
        
        # Normalized match
        elif not match_found:
            norm_player = normalize_name(player_name)
            if norm_player in norm_prices:
                match_found = True
                match_type = "normalized"
                match_price = norm_prices[norm_player]
                match_name = norm_player
        
        # Variant match
        if not match_found:
            for variant in variants:
                if variant in norm_prices:
                    match_found = True
                    match_type = "variant"
                    match_price = norm_prices[variant]
                    match_name = variant
                    break
        
        # Fuzzy match as last resort
        if not match_found:
            best_match = None
            best_ratio = 0.0
            
            for price_name in norm_prices.keys():
                ratio = difflib.SequenceMatcher(None, normalize_name(player_name), price_name).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = price_name
            
            if best_match and best_ratio > 0.8:
                match_found = True
                match_type = "fuzzy"
                match_price = norm_prices[best_match]
                match_name = f"{best_match} (confidence: {best_ratio:.2f})"
        
        # Store result
        if match_found:
            matched_count += 1
            
        results.append({
            "player_name": player_name,
            "position": player.get('position', '?'),
            "team": player.get('team', '?'),
            "match_found": match_found,
            "match_type": match_type if match_found else "none",
            "matched_name": match_name if match_found else None,
            "price": match_price if match_found else None,
            "variants": variants[:3]  # Just show first few variants
        })
    
    # Print summary
    print(f"\nResults Summary:")
    print(f"- Total players: {len(players)}")
    print(f"- Matched players: {matched_count}")
    print(f"- Unmatched players: {len(players) - matched_count}")
    
    # Print sample of unmatched players
    print("\nSample of unmatched players:")
    unmatched = [r for r in results if not r['match_found']]
    for i, r in enumerate(unmatched[:10], 1):
        print(f"{i}. {r['player_name']} ({r['position']}, {r['team']}) - Variants: {r['variants']}")
    
    # Save results to file
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "total_players": len(players),
                    "matched_count": matched_count,
                    "unmatched_count": len(players) - matched_count,
                    "results": results
                }, f, indent=2, ensure_ascii=False)
            print(f"\nDetailed results saved to {output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")

def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python debug_price_matching.py <player_data_file> <price_data_file> [output_file]")
        return 1
    
    player_file = sys.argv[1]
    price_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else "price_matching_debug.json"
    
    players = load_player_data(player_file)
    prices = load_price_data(price_file)
    
    if not players:
        print("Error: No player data loaded")
        return 1
    
    if not prices:
        print("Error: No price data loaded")
        return 1
    
    analyze_price_matching(players, prices, output_file)
    
    print("\nTo use these results for manual matching, you can add explicit mappings to:")
    print("data_fetch.py -> create_common_player_mappings() method")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
