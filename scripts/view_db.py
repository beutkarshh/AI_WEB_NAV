#!/usr/bin/env python3
"""
Simple script to view data from the navigation database
"""
import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "artifacts" / "nav.db"

def view_recent_runs():
    """Show recent search runs"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT query, started_at, items_kept, duration_ms 
        FROM runs 
        ORDER BY started_at DESC 
        LIMIT 10
    """, conn)
    print("Recent Search Runs:")
    print(df.to_string(index=False))
    conn.close()

def view_samsung_phones(max_price=50000):
    """Show Samsung phones under specified price"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT title, price_inr, rating, brand
        FROM items 
        WHERE title LIKE '%Samsung%' AND price_inr <= ?
        ORDER BY price_inr 
        LIMIT 20
    """, conn, params=(max_price,))
    print(f"\nSamsung Phones Under ₹{max_price:,}:")
    print(df.to_string(index=False))
    conn.close()

def view_all_items():
    """Show all items in database"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT COUNT(*) as total FROM items", conn)
    total = df.iloc[0]['total']
    print(f"\nTotal items in database: {total}")
    
    # Show sample
    df = pd.read_sql_query("""
        SELECT title, price_inr, rating, brand
        FROM items 
        ORDER BY id DESC 
        LIMIT 10
    """, conn)
    print("\nRecent 10 items:")
    print(df.to_string(index=False))
    conn.close()

if __name__ == "__main__":
    print(f"Database location: {DB_PATH}")
    view_recent_runs()
    view_samsung_phones()
    view_all_items()