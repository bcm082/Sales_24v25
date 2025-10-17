#!/usr/bin/env python3
"""
Data Preprocessing Script for Sales Comparison App

This script reads raw sales and inventory data files, extracts only the necessary columns,
and saves them as optimized CSV files for faster loading in the Streamlit app.

Run this script whenever you update the source data files.
"""

import pandas as pd
import glob
import os
from datetime import datetime

def preprocess_sales_data(year):
    """Load and consolidate all sales files for a given year into a single CSV"""
    sales_dir = f"{year}_Sales"

    if not os.path.exists(sales_dir):
        print(f"⚠️  Directory {sales_dir} not found! Skipping...")
        return False

    files = sorted(glob.glob(f"{sales_dir}/*.txt"))

    if not files:
        print(f"⚠️  No files found in {sales_dir}! Skipping...")
        return False

    print(f"\n📂 Processing {year} sales data...")
    print(f"   Found {len(files)} files")

    all_dfs = []

    for file_path in files:
        try:
            # Extract month from filename (e.g., "9-2024.txt" -> 9)
            month = int(os.path.basename(file_path).split('-')[0])

            # Read only necessary columns
            df = pd.read_csv(
                file_path,
                sep='\t',
                encoding='utf-8',
                encoding_errors='ignore',
                usecols=['sku', 'asin', 'purchase-date', 'quantity'],
                on_bad_lines='skip'
            )

            # Add month column
            df['month'] = month

            # Fill missing quantity with 1
            df['quantity'] = df['quantity'].fillna(1).astype(int)

            # Drop rows with missing sku or asin
            df = df.dropna(subset=['sku', 'asin'])

            # Rename for consistency
            df = df.rename(columns={'purchase-date': 'purchase_date'})

            all_dfs.append(df)
            print(f"   ✓ Processed {os.path.basename(file_path)}: {len(df):,} rows")

        except Exception as e:
            print(f"   ✗ Error processing {os.path.basename(file_path)}: {e}")
            continue

    if all_dfs:
        # Combine all dataframes
        combined_df = pd.concat(all_dfs, ignore_index=True)

        # Create cleaned_data directory if it doesn't exist
        os.makedirs('cleaned_data', exist_ok=True)

        # Save to CSV
        output_file = f'cleaned_data/{year}_sales.csv'
        combined_df.to_csv(output_file, index=False)

        print(f"   ✅ Saved {len(combined_df):,} total rows to {output_file}")
        print(f"   📊 File size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")
        return True
    else:
        print(f"   ✗ No data processed for {year}")
        return False

def preprocess_inventory_data():
    """Load and clean inventory data"""
    inventory_file = "Inventory.txt"

    if not os.path.exists(inventory_file):
        print(f"\n⚠️  Inventory file not found: {inventory_file}")
        return False

    print(f"\n📂 Processing inventory data...")

    try:
        # Read only necessary columns
        df = pd.read_csv(
            inventory_file,
            sep='\t',
            encoding='utf-8',
            encoding_errors='ignore',
            usecols=['seller-sku', 'asin1', 'price', 'quantity'],
            on_bad_lines='skip'
        )

        # Rename columns for consistency
        df = df.rename(columns={
            'seller-sku': 'sku',
            'asin1': 'asin',
            'price': 'current_price',
            'quantity': 'current_inventory'
        })

        # Clean data
        df = df.dropna(subset=['sku', 'asin'])
        df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce').fillna(0)
        df['current_inventory'] = pd.to_numeric(df['current_inventory'], errors='coerce').fillna(0).astype(int)

        # Create cleaned_data directory if it doesn't exist
        os.makedirs('cleaned_data', exist_ok=True)

        # Save to CSV
        output_file = 'cleaned_data/inventory.csv'
        df.to_csv(output_file, index=False)

        print(f"   ✅ Saved {len(df):,} rows to {output_file}")
        print(f"   📊 File size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")
        return True

    except Exception as e:
        print(f"   ✗ Error processing inventory file: {e}")
        return False

def main():
    """Main preprocessing function"""
    print("=" * 60)
    print("🧹 DATA PREPROCESSING FOR SALES COMPARISON APP")
    print("=" * 60)

    start_time = datetime.now()

    # Process sales data for both years
    success_2024 = preprocess_sales_data('2024')
    success_2025 = preprocess_sales_data('2025')

    # Process inventory data
    success_inventory = preprocess_inventory_data()

    # Summary
    print("\n" + "=" * 60)
    print("📋 PREPROCESSING SUMMARY")
    print("=" * 60)
    print(f"2024 Sales Data: {'✅ Success' if success_2024 else '❌ Failed/Skipped'}")
    print(f"2025 Sales Data: {'✅ Success' if success_2025 else '❌ Failed/Skipped'}")
    print(f"Inventory Data:  {'✅ Success' if success_inventory else '❌ Failed/Skipped'}")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n⏱️  Total processing time: {elapsed:.2f} seconds")

    if success_2024 or success_2025 or success_inventory:
        print("\n✨ Preprocessed data saved to 'cleaned_data/' directory")
        print("   You can now run the Streamlit app with optimized data!")
    else:
        print("\n⚠️  No data was successfully preprocessed")

    print("=" * 60)

if __name__ == "__main__":
    main()
