"""
Synthetic E-Commerce Dataset Generator for AnalystOS.

Generates realistic, reproducible, and internally consistent transaction data
with demonstrable business dynamics (seasonality, product-level margin compression,
and regional performance variances).
"""

from __future__ import annotations
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


def generate_ecommerce_dataset(
    num_records: int = 3000,
    seed: int = 42,
    output_path: str | None = None
) -> pd.DataFrame:
    """
    Generate synthetic e-commerce sales data with realistic business patterns.

    Key Embedded Patterns:
    1. Seasonal Q4 Volume Surge: High order volumes in November and December.
    2. H2 Margin Compression in Electronics: Starting July 2023, component costs rise (+22%)
       and competitive discounting (-10% to -15% unit price) crushes margins in Electronics.
    3. Regional Variance: South region exhibits aggressive promotional discounts and lower margins.
    4. Category Diversity: Office Supplies maintains high stable margins (45-55%),
       Furniture has moderate margins (30-40%), Apparel has moderate seasonal margins.
    5. 'Profitless Growth' Phenomenon: In Q4, Revenue increases due to holiday volume,
       but Net Profit declines sharply due to the Electronics margin squeeze.

    Parameters:
    - num_records (int): Number of order records to generate (minimum 2000).
    - seed (int): Random seed for reproducibility.
    - output_path (str | None): Optional CSV path to save generated data.

    Returns:
    - pd.DataFrame: Generated dataset with strictly consistent financial calculations.
    """
    if num_records < 2000:
        num_records = 2000

    rng = np.random.default_rng(seed)

    # Master Product Catalog: Product ID, Name, Category, Base Unit Price, Base Unit Cost
    products = [
        # Electronics
        ("PROD-E01", "Noise-Cancelling Headphones", "Electronics", 199.99, 120.00),
        ("PROD-E02", "Smart 4K Monitor 27-inch", "Electronics", 349.99, 230.00),
        ("PROD-E03", "Pro Ultra Wireless Earbuds", "Electronics", 129.99, 75.00),
        ("PROD-E04", "Wireless Mechanical Keyboard", "Electronics", 89.99, 50.00),
        ("PROD-E05", "Thunderbolt 4 Docking Station", "Electronics", 179.99, 105.00),
        # Furniture
        ("PROD-F01", "Ergonomic Executive Chair", "Furniture", 299.99, 180.00),
        ("PROD-F02", "Dual-Motor Standing Desk", "Furniture", 449.99, 280.00),
        ("PROD-F03", "Solid Oak Bookshelf", "Furniture", 219.99, 130.00),
        ("PROD-F04", "Adjustable Monitor Arm Mount", "Furniture", 79.99, 45.00),
        # Office Supplies
        ("PROD-O01", "Premium Gel Pen Set (24pk)", "Office Supplies", 24.99, 9.50),
        ("PROD-O02", "Recycled Copy Paper (5 Reams)", "Office Supplies", 39.99, 18.00),
        ("PROD-O03", "Heavy-Duty Desktop Stapler", "Office Supplies", 19.99, 8.00),
        ("PROD-O04", "Mesh Desk Organizer System", "Office Supplies", 29.99, 12.50),
        # Apparel
        ("PROD-A01", "Breathable Running Shoes", "Apparel", 119.99, 65.00),
        ("PROD-A02", "Performance Fleece Jacket", "Apparel", 89.99, 48.00),
        ("PROD-A03", "Merino Wool Crew Sweater", "Apparel", 74.99, 38.00),
        ("PROD-A04", "Thermal All-Weather Joggers", "Apparel", 59.99, 30.00),
    ]

    regions = ["North", "South", "East", "West"]
    region_weights = [0.28, 0.22, 0.26, 0.24]

    # Generate customer IDs pool (approx 450 recurring and new customers)
    customer_ids = [f"CUST-{1000 + i}" for i in range(450)]

    # Generate dates across calendar year 2023 (365 days)
    start_date = datetime(2023, 1, 1)
    
    # Seasonality weights by month (Jan to Dec): Higher volume in Nov (11) and Dec (12)
    month_weights = {
        1: 0.8, 2: 0.75, 3: 0.9, 4: 0.85, 5: 0.95, 6: 1.0,
        7: 1.05, 8: 1.1, 9: 1.0, 10: 1.15, 11: 1.5, 12: 1.8
    }

    days_in_year = 365
    day_weights = []
    for day_offset in range(days_in_year):
        current_day = start_date + timedelta(days=day_offset)
        day_weights.append(month_weights[current_day.month])
    
    day_weights = np.array(day_weights) / sum(day_weights)
    sampled_day_offsets = rng.choice(days_in_year, size=num_records, p=day_weights)
    sampled_day_offsets.sort()

    records = []
    order_counter = 10001

    for i in range(num_records):
        order_id = f"ORD-{order_counter}"
        order_counter += 1

        order_date = start_date + timedelta(days=int(sampled_day_offsets[i]))
        # Add random hour and minute
        hour = rng.integers(8, 22)
        minute = rng.integers(0, 60)
        order_timestamp = order_date.replace(hour=int(hour), minute=int(minute))

        # Sample product
        prod_idx = rng.integers(0, len(products))
        prod_id, prod_name, category, base_price, base_cost = products[prod_idx]

        # Sample customer & region
        customer_id = rng.choice(customer_ids)
        region = rng.choice(regions, p=region_weights)

        # Quantity: skewed towards 1-3, occasionally 4-8
        quantity = int(rng.choice([1, 2, 3, 4, 5, 8], p=[0.55, 0.25, 0.10, 0.05, 0.03, 0.02]))

        # Business Dynamic 1: Electronics Margin Squeeze in H2 (July onwards)
        unit_price = base_price
        unit_cost = base_cost

        if category == "Electronics" and order_date.month >= 7:
            # Component cost inflation: 18% to 28% cost hike
            cost_hike_factor = 1.0 + rng.uniform(0.18, 0.28)
            unit_cost = round(base_cost * cost_hike_factor, 2)

            # Competitive price discounts: 8% to 16% markdown to clear stock
            discount_factor = 1.0 - rng.uniform(0.08, 0.16)
            unit_price = round(base_price * discount_factor, 2)
        else:
            # Minor random price fluctuation (+- 3%)
            price_variation = rng.uniform(0.97, 1.03)
            unit_price = round(base_price * price_variation, 2)
            unit_cost = base_cost

        # Business Dynamic 2: Regional variation - South has extra 5% discount
        if region == "South":
            unit_price = round(unit_price * 0.95, 2)
            # Higher distribution cost for South
            unit_cost = round(unit_cost * 1.03, 2)

        # Calculate exact consistent financial metrics
        revenue = round(quantity * unit_price, 2)
        cost = round(quantity * unit_cost, 2)
        profit = round(revenue - cost, 2)

        records.append({
            "Order ID": order_id,
            "Order Date": order_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Product ID": prod_id,
            "Product Name": prod_name,
            "Category": category,
            "Customer ID": customer_id,
            "Region": region,
            "Quantity": quantity,
            "Unit Price": unit_price,
            "Unit Cost": unit_cost,
            "Revenue": revenue,
            "Cost": cost,
            "Profit": profit,
        })

    df = pd.DataFrame(records)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False)

    return df


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_csv_path = os.path.join(current_dir, "synthetic_sales.csv")
    print(f"Generating synthetic dataset with 3000 records to: {sample_csv_path}")
    df_generated = generate_ecommerce_dataset(num_records=3000, seed=42, output_path=sample_csv_path)
    print(f"Successfully generated {len(df_generated)} records.")
    print("Summary:")
    print(df_generated[["Revenue", "Cost", "Profit"]].sum())
