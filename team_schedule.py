"""
NHL Team Schedule Helper
Retrieves and displays team schedules and players for specific game days
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from data_fetch import NHLDataFetcher

def format_date(date_str):
    """Format date string to display format"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return date.strftime("%A, %b %d, %Y")

def main():
    parser = argparse.ArgumentParser(description='NHL Team Schedule Helper')
    parser.add_argument('--date', type=str, default='today',
                        help='Date to check (YYYY-MM-DD format or "today")')
    parser.add_argument('--team', type=str, 
                        help='Filter by specific team (e.g., TOR)')
    parser.add_argument('--days', type=int, default=1,
                        help='Number of days to check (default: 1)')
    
    args = parser.parse_args()
    
    # Process date
    if args.date.lower() == 'today':
        start_date = datetime.now()
    else:
        try:
            start_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD.")
            return 1
    
    # Initialize fetcher
    fetcher = NHLDataFetcher()
    
    # Check schedule for specified days
    print(f"NHL Schedule for the next {args.days} day(s):\n")
    
    for day_offset in range(args.days):
        check_date = start_date + timedelta(days=day_offset)
        date_str = check_date.strftime('%Y-%m-%d')
        
        print(f"Date: {format_date(date_str)}")
        print("-" * 60)
        
        # Get schedule for this date
        schedule = fetcher.get_team_schedule(date_str)
        teams_playing = schedule.get(date_str, [])
        
        # Filter by team if specified
        if args.team:
            team_abbr = args.team.upper()
            if team_abbr in [t.upper() for t in teams_playing]:
                teams_playing = [t for t in teams_playing if t.upper() == team_abbr]
            else:
                print(f"{args.team} is not playing on {date_str}\n")
                teams_playing = []
        
        if teams_playing:
            print(f"Teams playing ({len(teams_playing)}): {', '.join(teams_playing)}")
            
            # Show some example players from these teams
            if args.team and len(teams_playing) == 1:
                print("\nLoading roster for detailed player information...")
                try:
                    roster = fetcher.fetch_team_roster(teams_playing[0])
                    print(f"\nKey players for {teams_playing[0]}:")
                    
                    # Format based on API response structure
                    if 'forwards' in roster and 'defensemen' in roster:
                        # Grouped format
                        for pos_group in ['forwards', 'defensemen', 'goalies']:
                            if pos_group in roster:
                                print(f"\n{pos_group.upper()}:")
                                for i, player in enumerate(roster.get(pos_group, [])[:5]):
                                    name = player.get('fullName', player.get('name', 'Unknown'))
                                    number = player.get('sweaterNumber', '')
                                    print(f"  #{number} {name}")
                    elif isinstance(roster, list):
                        # List format
                        players_by_pos = {'F': [], 'D': [], 'G': []}
                        for player in roster:
                            pos = player.get('position', {}).get('code', 'F')
                            if pos in players_by_pos:
                                players_by_pos[pos].append(player)
                        
                        for pos, players in players_by_pos.items():
                            if players:
                                print(f"\n{pos}:")
                                for i, player in enumerate(players[:5]):
                                    name = player.get('fullName', player.get('name', 'Unknown'))
                                    number = player.get('sweaterNumber', '')
                                    print(f"  #{number} {name}")
                except Exception as e:
                    print(f"Error loading roster: {e}")
        else:
            print("No games scheduled for this date")
        
        print()  # Add blank line between days
    
    # Suggest command to run for lineup optimization
    if teams_playing:
        team_list = ",".join(teams_playing)
        print("\nTo create a lineup with these teams, run:")
        print(f"python main.py --source api --teams {team_list} --prices hraci_ceny.csv")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
