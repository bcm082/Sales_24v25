# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based seasonal e-commerce analytics system designed for Halloween/seasonal sales optimization. The project analyzes inventory, sales performance, and provides automated pricing recommendations based on historical data patterns and weekly targets.

## Core Components

### Main Scripts
- `daily_pricing_calculator_simple.py` - Daily pricing optimization based on gap analysis against seasonal targets
- `weekly_performance_tracker.py` - Retrospective performance analysis with two modes: actual prior week analysis and Halloween week analysis

### Data Files
- `Inventory.txt` - Current inventory levels, prices, and product metadata (tab-delimited)
- `2025_Sales/[month]-2025.txt` - Monthly sales data files (tab-delimited)  
- `2024_Sales/[month]-2024.txt` - Historical sales data for pattern analysis
- Generated CSV reports with timestamped analysis results

### Documentation
- `README_pricing_script.md` - Detailed usage guide for the pricing calculator
- `README_performance_tracker.md` - Usage guide for performance analysis

## Key Architecture Patterns

### Data Processing Pipeline
1. **Data Loading**: Tab-delimited file parsing with error handling for encoding issues
2. **Date Processing**: ISO format parsing with timezone handling (`datetime.fromisoformat`)
3. **Key Matching**: SKU-first matching with ASIN fallback for sales/inventory correlation
4. **Gap Analysis**: Performance vs target calculations using predefined seasonal patterns

### Seasonal Targeting System
The system uses empirically-derived weekly targets based on 2024 analysis:
- Week 1-8 progression: 2.2% → 3.0% → 3.8% → 7.3% → 10.3% → 16.4% → 28.0% → 28.0%
- Automatic week calculation based on September 1st season start
- Season-to-date vs weekly performance tracking

### Pricing Algorithm
Five-tier pricing action system based on performance gaps:
- `AGGRESSIVE_DISCOUNT` (gap < -20%): 15-25% price reduction
- `MODERATE_DISCOUNT` (gap -20% to -10%): 8-15% price reduction  
- `HOLD_STEADY` (gap -10% to +10%): No change
- `MODERATE_INCREASE` (gap +10% to +25%): 5-12% price increase
- `PREMIUM_PRICING` (gap > +25%): 12-20% price increase

## Common Development Tasks

### Running Analysis Scripts
```bash
# Daily pricing recommendations
python daily_pricing_calculator_simple.py

# Performance analysis - prior week (default)
python weekly_performance_tracker.py

# Performance analysis - specific Halloween week (1-8)
python weekly_performance_tracker.py [week_number]
```

### Environment Setup
The project uses a Python virtual environment in `2025_Season_ENV/`:
```bash
# Activate environment (if needed)
source 2025_Season_ENV/bin/activate

# The scripts use only standard library modules (csv, datetime, os, glob, collections, random)
```

### Working with Data Files
- **Inventory.txt**: Tab-delimited with columns: seller-sku, price, quantity, asin1
- **Sales files**: Tab-delimited with columns: sku, asin, purchase-date, quantity (optional)
- All file reading includes `encoding='utf-8', errors='ignore'` for robustness
- Date fields use ISO format parsing with timezone normalization

### Testing Script Behavior
- Scripts include built-in error handling and progress reporting
- Generated CSV files are timestamped for tracking changes over time
- Console output provides immediate performance summaries
- Both scripts can run with missing or incomplete data

## File Patterns and Conventions

### Generated Reports
- `pricing_recommendations_week[X]_[YYYYMMDD_HHMMSS].csv`
- `performance_analysis_week[X]_[YYYYMMDD_HHMMSS].csv`  
- `prior_week_analysis_[YYYYMMDD]_[YYYYMMDD_HHMMSS].csv`

### Data Processing Conventions
- Use `defaultdict(int)` for aggregating sales by SKU/ASIN
- Prefer SKU matching over ASIN when both available
- Round financial calculations to 2 decimal places
- Handle missing quantity columns by defaulting to 1

### Error Handling Patterns
- Try/except blocks around all file operations
- Continue processing on individual row failures
- Provide informative console output about data loading success/failures
- Graceful degradation when data files are missing

## Seasonal Business Logic

### Week Calculation Logic
- Season starts September 1st each year
- Automatic year adjustment based on current date
- Week boundaries: Monday-Sunday spans
- Week 8 captures October 20-31 (extended final week)

### Performance Classification
Uses percentage-based grading system:
- EXCELLENT: +25% above target
- GOOD: +10% to +25% above target  
- ON_TARGET: -10% to +10% of target
- BELOW_TARGET: -10% to -25% below target
- POOR: >-25% below target

### Inventory Estimation
Current quantity + season sales to date = estimated starting inventory
This accounts for inventory depletion since season start without requiring historical snapshots.