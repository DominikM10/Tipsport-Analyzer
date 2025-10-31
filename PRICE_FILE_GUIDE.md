# Price File Guide

## File Format

Your price file should be a CSV file with player names and prices. The script supports two formats:

### Format 1: Split Decimal (Recommended)
```csv
Makar C.,30,9
McDavid C.,21,9
Matthews A.,24,5
```

This means:
- Makar C. costs 30.9M
- McDavid C. costs 21.9M
- Matthews A. costs 24.5M

### Format 2: Single Price Column
```csv
Makar C.,30.9
McDavid C.,21.9
Matthews A.,24.5
```

## Player Name Format

**Important:** Player names must be in the format: `LastName FirstInitial.`

Examples:
- Connor McDavid → `McDavid C.`
- Auston Matthews → `Matthews A.`
- Cale Makar → `Makar C.`

## File Location

Place your price file in one of these locations:

1. **Same directory as the script** (Recommended)
   ```
   c:\Users\idoms\OneDrive\Desktop\Tipsport Analyzer\hraci_ceny.csv
   ```

2. **Your Desktop**
   ```
   C:\Users\idoms\Desktop\hraci_ceny.csv
   ```

3. **Any custom location** - you'll be prompted to enter the path

## How to Use

### Method 1: Place file in script directory
```bash
# Just put hraci_ceny.csv in the same folder as main.py
python main.py --source api
```

### Method 2: Specify path explicitly
```bash
python main.py --source api --prices "C:\Users\idoms\Desktop\hraci_ceny.csv"
```

### Method 3: Let the script prompt you
```bash
# Run without --prices argument
python main.py --source api

# When prompted, enter the full path:
# Enter the full path to your price file: C:\Users\idoms\Desktop\hraci_ceny.csv
```

## Troubleshooting

### "No players were matched with prices"

This usually means the player names in your price file don't match the names from the API.

**Check:**
1. Open `player_price_matching.json` - this shows why players didn't match
2. Make sure names use format: `LastName FirstInitial.`
3. Check for special characters (é, č, ř, etc.)

**Example fixes:**
- `Connor McDavid` → `McDavid C.`
- `David Pastrnak` → `Pastrňák D.` or `Pastrnak D.`

### "File not found"

**On Windows, copy the path:**
1. Right-click the file in File Explorer
2. Hold Shift and click "Copy as path"
3. Paste when prompted (quotes will be removed automatically)

**Example paths:**
```
C:\Users\idoms\OneDrive\Desktop\Tipsport Analyzer\hraci_ceny.csv
C:\Users\idoms\Desktop\hraci_ceny.csv
C:\temp\prices.csv
```

### Debug Mode

To see detailed matching information:
```bash
python main.py --source api --prices hraci_ceny.csv
```

Then check these files:
- `hraci_ceny_parsed.json` - Shows what was parsed from the price file
- `player_price_matching.json` - Shows detailed matching results
