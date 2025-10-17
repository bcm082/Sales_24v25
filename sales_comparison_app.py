import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pytz

# Page configuration
st.set_page_config(page_title="Sales Comparison 2024 vs 2025", layout="wide")

@st.cache_data
def load_sales_data(year, cutoff_date=None):
    """Load preprocessed sales data from CSV - much faster!"""
    csv_file = f"cleaned_data/{year}_sales.csv"

    if not os.path.exists(csv_file):
        st.error(f"Preprocessed data file not found: {csv_file}\n\nPlease run 'python preprocess_data.py' first!")
        return pd.DataFrame()

    try:
        # Load preprocessed CSV (much faster than parsing multiple txt files)
        df = pd.read_csv(csv_file)

        # Apply date filter if cutoff_date is provided
        if cutoff_date:
            # Parse purchase_date and filter
            df['purchase_datetime'] = pd.to_datetime(df['purchase_date'], errors='coerce')
            df = df[df['purchase_datetime'] <= cutoff_date]
            df = df.drop(columns=['purchase_datetime'])

        return df

    except Exception as e:
        st.error(f"Error loading preprocessed data: {e}")
        return pd.DataFrame()

@st.cache_data
def load_inventory_data():
    """Load preprocessed inventory data from CSV"""
    csv_file = "cleaned_data/inventory.csv"

    if not os.path.exists(csv_file):
        st.warning(f"Preprocessed inventory file not found: {csv_file}\n\nPlease run 'python preprocess_data.py' first!")
        return pd.DataFrame()

    try:
        # Load preprocessed CSV (already cleaned and formatted)
        df = pd.read_csv(csv_file)
        return df

    except Exception as e:
        st.warning(f"Error loading preprocessed inventory: {e}")
        return pd.DataFrame()

@st.cache_data
def create_sku_level_data(year_2024_data, year_2025_data, inventory_data):
    """Pre-compute SKU-level aggregations for fast searching"""

    df_2024 = pd.DataFrame(year_2024_data)
    df_2025 = pd.DataFrame(year_2025_data)
    inventory_df = pd.DataFrame(inventory_data)

    # Aggregate by SKU for 2024
    sku_totals_2024 = df_2024.groupby('sku').agg({
        'quantity': 'sum',
        'asin': 'first'
    }).reset_index()
    sku_totals_2024.columns = ['sku', 'total_2024', 'asin']

    # Monthly data for 2024
    monthly_2024 = df_2024.groupby(['sku', 'month'])['quantity'].sum().reset_index()
    monthly_2024_dict = monthly_2024.groupby('sku').apply(
        lambda x: dict(zip(x['month'], x['quantity']))
    ).to_dict()

    # Aggregate by SKU for 2025
    sku_totals_2025 = df_2025.groupby('sku').agg({
        'quantity': 'sum',
        'asin': 'first'
    }).reset_index()
    sku_totals_2025.columns = ['sku', 'total_2025', 'asin_2025']

    # Monthly data for 2025
    monthly_2025 = df_2025.groupby(['sku', 'month'])['quantity'].sum().reset_index()
    monthly_2025_dict = monthly_2025.groupby('sku').apply(
        lambda x: dict(zip(x['month'], x['quantity']))
    ).to_dict()

    # Merge
    sku_data = pd.merge(sku_totals_2024, sku_totals_2025[['sku', 'total_2025']], on='sku', how='outer')

    # Fill NaN values
    sku_data['total_2024'] = sku_data['total_2024'].fillna(0).astype(int)
    sku_data['total_2025'] = sku_data['total_2025'].fillna(0).astype(int)

    # Fill ASIN from either year
    if not df_2025.empty:
        asin_map_2025 = df_2025.groupby('sku')['asin'].first().to_dict()
        sku_data['asin'] = sku_data['asin'].fillna(sku_data['sku'].map(asin_map_2025))

    sku_data['asin'] = sku_data['asin'].fillna('N/A')

    # Calculate metrics
    sku_data['difference'] = sku_data['total_2025'] - sku_data['total_2024']
    sku_data['change_pct'] = sku_data.apply(
        lambda row: round((row['difference'] / row['total_2024'] * 100), 1) if row['total_2024'] > 0 else 0,
        axis=1
    )

    # Add monthly data
    sku_data['monthly_2024'] = sku_data['sku'].map(monthly_2024_dict).apply(lambda x: x if isinstance(x, dict) else {})
    sku_data['monthly_2025'] = sku_data['sku'].map(monthly_2025_dict).apply(lambda x: x if isinstance(x, dict) else {})

    # Merge inventory data if available
    if not inventory_df.empty:
        sku_data = sku_data.merge(
            inventory_df[['sku', 'current_inventory', 'current_price']],
            on='sku',
            how='left'
        )

        # Fill NaN values
        sku_data['current_inventory'] = sku_data['current_inventory'].fillna(0).astype(int)
        sku_data['current_price'] = sku_data['current_price'].fillna(0).round(2)

    return sku_data

@st.cache_data
def create_comparison_table(year_2024_data, year_2025_data, inventory_data):
    """Create a comprehensive comparison table - optimized version"""

    df_2024 = pd.DataFrame(year_2024_data)
    df_2025 = pd.DataFrame(year_2025_data)
    inventory_df = pd.DataFrame(inventory_data)

    # Pre-aggregate all data at once for better performance
    agg_2024 = df_2024.groupby('asin').agg({
        'quantity': 'sum',
        'sku': lambda x: sorted(set(x))
    }).reset_index()
    agg_2024.columns = ['asin', 'total_2024', 'skus_2024']

    agg_2025 = df_2025.groupby('asin').agg({
        'quantity': 'sum',
        'sku': lambda x: sorted(set(x))
    }).reset_index()
    agg_2025.columns = ['asin', 'total_2025', 'skus_2025']

    # Get monthly aggregations
    monthly_2024 = df_2024.groupby(['asin', 'month'])['quantity'].sum().reset_index()
    monthly_2024_dict = monthly_2024.groupby('asin').apply(
        lambda x: dict(zip(x['month'], x['quantity']))
    ).to_dict()

    monthly_2025 = df_2025.groupby(['asin', 'month'])['quantity'].sum().reset_index()
    monthly_2025_dict = monthly_2025.groupby('asin').apply(
        lambda x: dict(zip(x['month'], x['quantity']))
    ).to_dict()

    # Merge the aggregations
    comparison = pd.merge(agg_2024, agg_2025, on='asin', how='outer')

    # Fill NaN values
    comparison['total_2024'] = comparison['total_2024'].fillna(0).astype(int)
    comparison['total_2025'] = comparison['total_2025'].fillna(0).astype(int)
    comparison['skus_2024'] = comparison['skus_2024'].apply(lambda x: x if isinstance(x, list) else [])
    comparison['skus_2025'] = comparison['skus_2025'].apply(lambda x: x if isinstance(x, list) else [])

    # Combine SKUs
    comparison['all_skus'] = comparison.apply(
        lambda row: sorted(set(row['skus_2024'] + row['skus_2025'])),
        axis=1
    )

    # Calculate differences and changes
    comparison['difference'] = comparison['total_2025'] - comparison['total_2024']
    comparison['change_pct'] = comparison.apply(
        lambda row: round((row['difference'] / row['total_2024'] * 100), 1) if row['total_2024'] > 0 else 0,
        axis=1
    )

    # Add monthly data
    comparison['monthly_2024'] = comparison['asin'].map(monthly_2024_dict).apply(lambda x: x if isinstance(x, dict) else {})
    comparison['monthly_2025'] = comparison['asin'].map(monthly_2025_dict).apply(lambda x: x if isinstance(x, dict) else {})

    # Create final dataframe
    result = pd.DataFrame({
        'ASIN': comparison['asin'],
        'SKUs': comparison['all_skus'].apply(lambda x: ', '.join(x)),
        'Total 2024': comparison['total_2024'],
        'Total 2025': comparison['total_2025'],
        'Difference': comparison['difference'],
        'Change %': comparison['change_pct'],
        'monthly_2024': comparison['monthly_2024'],
        'monthly_2025': comparison['monthly_2025']
    })

    # Merge inventory data if available
    if not inventory_df.empty:
        # Aggregate inventory by ASIN
        inventory_by_asin = inventory_df.groupby('asin').agg({
            'current_inventory': 'sum',
            'current_price': 'mean'
        }).reset_index()
        inventory_by_asin['current_price'] = inventory_by_asin['current_price'].round(2)

        # Merge with result
        result = result.merge(
            inventory_by_asin[['asin', 'current_inventory', 'current_price']],
            left_on='ASIN',
            right_on='asin',
            how='left'
        ).drop(columns=['asin'])

        # Fill NaN values
        result['current_inventory'] = result['current_inventory'].fillna(0).astype(int)
        result['current_price'] = result['current_price'].fillna(0).round(2)

    return result

# Main app
st.title("📊 Sales Comparison: 2024 vs 2025")

# Calculate cutoff dates for fair comparison (timezone-aware for UTC comparison)
today = datetime.now()
utc = pytz.UTC
cutoff_2025 = utc.localize(datetime(today.year, today.month, today.day, 23, 59, 59))
cutoff_2024 = utc.localize(datetime(2024, today.month, today.day, 23, 59, 59))

# Display comparison period
st.info(f"📅 **Comparison Period:** January 1 - {today.strftime('%B %d')} (Year-to-Date through today)")

# Add cache clear button in sidebar
with st.sidebar:
    st.header("Settings")
    if st.button("🔄 Refresh Data", help="Clear cache and reload data from files"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.info("📝 **Note:** This app uses preprocessed data.\n\nIf you've updated the source files, run:\n```python preprocess_data.py```")

    st.divider()
    st.caption(f"**Comparing:**")
    st.caption(f"2024: Jan 1 - {cutoff_2024.strftime('%b %d, %Y')}")
    st.caption(f"2025: Jan 1 - {cutoff_2025.strftime('%b %d, %Y')}")

# Load data with single spinner
with st.spinner("Loading preprocessed data..."):
    df_2024 = load_sales_data('2024', cutoff_2024)
    df_2025 = load_sales_data('2025', cutoff_2025)

if df_2024.empty and df_2025.empty:
    st.error("No sales data found! Please run 'python preprocess_data.py' to generate preprocessed data files.")
    st.stop()

# Load inventory data
inventory_df = load_inventory_data()

# Create comparison tables (cached for performance - includes inventory merging)
with st.spinner("Analyzing data..."):
    comparison_df = create_comparison_table(
        df_2024.to_dict('records'),
        df_2025.to_dict('records'),
        inventory_df.to_dict('records') if not inventory_df.empty else []
    )
    # Pre-compute SKU-level data for fast searching (includes inventory merging)
    sku_level_df = create_sku_level_data(
        df_2024.to_dict('records'),
        df_2025.to_dict('records'),
        inventory_df.to_dict('records') if not inventory_df.empty else []
    )

# Summary statistics
st.header("📈 Year-to-Date Summary")

if not inventory_df.empty:
    col1, col2, col3, col4 = st.columns(4)
else:
    col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Units 2024 (YTD)", f"{df_2024['quantity'].sum():,}")
    st.metric("Unique ASINs 2024", len(df_2024['asin'].unique()))

with col2:
    st.metric("Total Units 2025 (YTD)", f"{df_2025['quantity'].sum():,}")
    st.metric("Unique ASINs 2025", len(df_2025['asin'].unique()))

with col3:
    year_diff = df_2025['quantity'].sum() - df_2024['quantity'].sum()
    year_pct = (year_diff / df_2024['quantity'].sum() * 100) if df_2024['quantity'].sum() > 0 else 0
    st.metric("YoY Change (Units)", f"{year_diff:+,}", f"{year_pct:+.1f}%")

if not inventory_df.empty:
    with col4:
        st.metric("Current Inventory", f"{inventory_df['current_inventory'].sum():,}")
        st.metric("Total SKUs in Stock", len(inventory_df[inventory_df['current_inventory'] > 0]))

# Filters
st.header("🔍 Filter Options")
col1, col2 = st.columns(2)

with col1:
    # Filter by change percentage
    change_filter = st.selectbox(
        "Filter by performance:",
        ["All", "Growing (>0%)", "Declining (<0%)", "New in 2025", "Not in 2025"]
    )

with col2:
    # Sort options
    sort_by = st.selectbox(
        "Sort by:",
        ["2025 YTD (High to Low)", "2024 YTD (High to Low)", "Change % (High to Low)",
         "Change % (Low to High)", "ASIN"]
    )

# Apply filters
filtered_df = comparison_df.copy()

if change_filter == "Growing (>0%)":
    filtered_df = filtered_df[filtered_df['Change %'] > 0]
elif change_filter == "Declining (<0%)":
    filtered_df = filtered_df[filtered_df['Change %'] < 0]
elif change_filter == "New in 2025":
    filtered_df = filtered_df[filtered_df['Total 2024'] == 0]
elif change_filter == "Not in 2025":
    filtered_df = filtered_df[filtered_df['Total 2025'] == 0]

# Apply sorting
if sort_by == "2025 YTD (High to Low)":
    filtered_df = filtered_df.sort_values('Total 2025', ascending=False)
elif sort_by == "2024 YTD (High to Low)":
    filtered_df = filtered_df.sort_values('Total 2024', ascending=False)
elif sort_by == "Change % (High to Low)":
    filtered_df = filtered_df.sort_values('Change %', ascending=False)
elif sort_by == "Change % (Low to High)":
    filtered_df = filtered_df.sort_values('Change %', ascending=True)
elif sort_by == "ASIN":
    filtered_df = filtered_df.sort_values('ASIN')

# Display main comparison table
st.header(f"📋 Year-to-Date Comparison by ASIN ({len(filtered_df)} items)")

if 'current_inventory' in filtered_df.columns:
    st.caption("💡 **Current Qty** and **Avg Price** show current inventory levels and average price from Inventory.txt")

# Create display dataframe
if 'current_inventory' in filtered_df.columns:
    display_df = filtered_df[['ASIN', 'SKUs', 'Total 2024', 'Total 2025', 'Difference', 'Change %', 'current_inventory', 'current_price']].copy()
    display_df = display_df.rename(columns={
        'Total 2024': '2024 (YTD)',
        'Total 2025': '2025 (YTD)',
        'current_inventory': 'Current Qty',
        'current_price': 'Avg Price'
    })
else:
    display_df = filtered_df[['ASIN', 'SKUs', 'Total 2024', 'Total 2025', 'Difference', 'Change %']].copy()
    display_df.columns = ['ASIN', 'SKUs', '2024 (YTD)', '2025 (YTD)', 'Difference', 'Change %']

# Color code the dataframe with better contrast
def highlight_change(row):
    if row['Change %'] > 10:
        # Light green background with dark text
        return ['background-color: #e8f5e9; color: #1b5e20'] * len(row)
    elif row['Change %'] < -10:
        # Light red background with dark text
        return ['background-color: #ffebee; color: #b71c1c'] * len(row)
    else:
        return [''] * len(row)

format_dict = {
    '2024 (YTD)': '{:,}',
    '2025 (YTD)': '{:,}',
    'Difference': '{:+,}',
    'Change %': '{:+.1f}%'
}

if 'Current Qty' in display_df.columns:
    format_dict['Current Qty'] = '{:,}'
    format_dict['Avg Price'] = '${:.2f}'

st.dataframe(
    display_df.style.apply(highlight_change, axis=1).format(format_dict),
    use_container_width=True,
    height=600
)

# SKU Search Feature
st.header("🔎 SKU Search")
st.write("Search for SKUs by partial match (e.g., 'aerosmith002' will find all sizes)")

sku_search = st.text_input("Enter SKU search term:", placeholder="e.g., aerosmith002")

# Trim whitespace from search input
if sku_search:
    sku_search = sku_search.strip()

if sku_search:
    # Filter pre-computed SKU data (very fast!)
    matching_skus = sku_level_df[sku_level_df['sku'].str.contains(sku_search, case=False, na=False)]

    if len(matching_skus) > 0:
        st.success(f"Found {len(matching_skus)} matching SKU(s)")

        # Prepare display data
        sku_comparison_df = matching_skus.copy()
        sku_comparison_df = sku_comparison_df.rename(columns={
            'sku': 'SKU',
            'asin': 'ASIN',
            'total_2024': '2024 (YTD)',
            'total_2025': '2025 (YTD)',
            'difference': 'Difference',
            'change_pct': 'Change %'
        })

        # Display summary table
        st.subheader(f"📊 SKU Comparison Results")

        if 'current_inventory' in sku_comparison_df.columns:
            st.caption("💡 **Current Qty** and **Price** show current inventory levels and pricing for each SKU")

        # Select columns based on what's available
        if 'current_inventory' in sku_comparison_df.columns:
            display_sku_df = sku_comparison_df[['SKU', 'ASIN', '2024 (YTD)', '2025 (YTD)', 'Difference', 'Change %', 'current_inventory', 'current_price']].copy()
            display_sku_df = display_sku_df.rename(columns={
                'current_inventory': 'Current Qty',
                'current_price': 'Price'
            })
        else:
            display_sku_df = sku_comparison_df[['SKU', 'ASIN', '2024 (YTD)', '2025 (YTD)', 'Difference', 'Change %']].copy()

        # Add totals row
        totals = {
            'SKU': 'TOTAL (All Sizes)',
            'ASIN': '',
            '2024 (YTD)': display_sku_df['2024 (YTD)'].sum(),
            '2025 (YTD)': display_sku_df['2025 (YTD)'].sum(),
            'Difference': display_sku_df['Difference'].sum(),
            'Change %': ((display_sku_df['2025 (YTD)'].sum() - display_sku_df['2024 (YTD)'].sum()) / display_sku_df['2024 (YTD)'].sum() * 100) if display_sku_df['2024 (YTD)'].sum() > 0 else 0
        }

        if 'Current Qty' in display_sku_df.columns:
            totals['Current Qty'] = display_sku_df['Current Qty'].sum()
            totals['Price'] = 0  # Don't total prices, use 0 for formatting

        totals_df = pd.DataFrame([totals])

        # Combine with totals
        display_with_totals = pd.concat([display_sku_df, totals_df], ignore_index=True)

        # Replace 0 with '-' in the Price column of the totals row
        if 'Price' in display_with_totals.columns:
            display_with_totals.loc[display_with_totals['SKU'] == 'TOTAL (All Sizes)', 'Price'] = None

        # Format dictionary
        sku_format_dict = {
            '2024 (YTD)': '{:,.0f}',
            '2025 (YTD)': '{:,.0f}',
            'Difference': '{:+,.0f}',
            'Change %': '{:+.1f}%'
        }

        if 'Current Qty' in display_with_totals.columns:
            sku_format_dict['Current Qty'] = '{:,.0f}'
            sku_format_dict['Price'] = '${:.2f}'

        st.dataframe(
            display_with_totals.style.format(sku_format_dict, na_rep='-'),
            use_container_width=True
        )

        # Monthly breakdown for selected SKU from search results
        st.subheader("📅 Monthly Breakdown by SKU")
        selected_sku = st.selectbox(
            "Select a SKU to view monthly details:",
            sku_comparison_df['SKU'].tolist(),
            key="sku_selector"
        )

        if selected_sku:
            selected_sku_row = sku_comparison_df[sku_comparison_df['SKU'] == selected_sku].iloc[0]

            st.write(f"**SKU:** {selected_sku}")
            st.write(f"**ASIN:** {selected_sku_row['ASIN']}")

            # Create monthly comparison table
            months = list(range(1, 13))
            monthly_data = []

            for month in months:
                qty_2024 = selected_sku_row['monthly_2024'].get(month, 0)
                qty_2025 = selected_sku_row['monthly_2025'].get(month, 0)
                diff = qty_2025 - qty_2024
                pct = ((qty_2025 - qty_2024) / qty_2024 * 100) if qty_2024 > 0 else 0

                monthly_data.append({
                    'Month': datetime(2024, month, 1).strftime('%B'),
                    '2024': int(qty_2024),
                    '2025': int(qty_2025),
                    'Difference': int(diff),
                    'Change %': round(pct, 1)
                })

            monthly_df = pd.DataFrame(monthly_data)

            col1, col2 = st.columns([2, 1])

            with col1:
                st.dataframe(
                    monthly_df.style.format({
                        '2024': '{:,}',
                        '2025': '{:,}',
                        'Difference': '{:+,}',
                        'Change %': '{:+.1f}%'
                    }),
                    use_container_width=True
                )

            with col2:
                # Chart
                chart_data = monthly_df.set_index('Month')[['2024', '2025']]
                st.bar_chart(chart_data)
    else:
        st.warning(f"No SKUs found matching '{sku_search}'")

st.divider()

# Monthly breakdown for selected ASIN
st.header("📅 Monthly Breakdown by ASIN")

selected_asin = st.selectbox(
    "Select an ASIN to view monthly details:",
    filtered_df['ASIN'].tolist()
)

if selected_asin:
    selected_row = filtered_df[filtered_df['ASIN'] == selected_asin].iloc[0]

    st.subheader(f"ASIN: {selected_asin}")
    st.write(f"**Associated SKUs:** {selected_row['SKUs']}")

    # Create monthly comparison table
    months = list(range(1, 13))
    monthly_data = []

    for month in months:
        qty_2024 = selected_row['monthly_2024'].get(month, 0)
        qty_2025 = selected_row['monthly_2025'].get(month, 0)
        diff = qty_2025 - qty_2024
        pct = ((qty_2025 - qty_2024) / qty_2024 * 100) if qty_2024 > 0 else 0

        monthly_data.append({
            'Month': datetime(2024, month, 1).strftime('%B'),
            '2024': int(qty_2024),
            '2025': int(qty_2025),
            'Difference': int(diff),
            'Change %': round(pct, 1)
        })

    monthly_df = pd.DataFrame(monthly_data)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.dataframe(
            monthly_df.style.format({
                '2024': '{:,}',
                '2025': '{:,}',
                'Difference': '{:+,}',
                'Change %': '{:+.1f}%'
            }),
            use_container_width=True
        )

    with col2:
        # Chart
        chart_data = monthly_df.set_index('Month')[['2024', '2025']]
        st.bar_chart(chart_data)

# Export functionality
st.header("💾 Export Data")

csv = display_df.to_csv(index=False)
st.download_button(
    label="Download YTD comparison as CSV",
    data=csv,
    file_name=f"ytd_sales_comparison_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

st.info(f"💡 **Color Legend:** Light green = Growing >10% | Light red = Declining >10% | **Note:** Comparing same date range (Jan 1 - {today.strftime('%b %d')}) for both years")
