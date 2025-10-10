#!/usr/bin/env python3
"""
Quick test script to demonstrate the API endpoints
Usage: python test_api.py (make sure server is running on port 8000)
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_quick_search():
    print("🔥 Testing Quick Search API...")
    response = requests.get(f"{BASE_URL}/search", params={
        "query": "phones under 15000",
        "mode": "quick"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Quick Search Success!")
        print(f"   Items found: {data.get('items_found', 0)}")
        print(f"   Mode: {data.get('mode')}")
        if data.get('results'):
            print(f"   First result: {data['results'][0].get('title', 'N/A')}")
    else:
        print(f"❌ Quick Search Failed: {response.status_code}")

def test_deep_search():
    print("\n🚀 Testing Deep Search API...")
    payload = {
        "query": "laptops under 50000", 
        "mode": "deep",
        "max_pages": 2
    }
    
    response = requests.post(f"{BASE_URL}/search", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Deep Search Success!")
        print(f"   Items found: {data.get('items_found', 0)}")
        print(f"   Mode: {data.get('mode')}")
        print(f"   Max pages: {data.get('max_pages')}")
        if data.get('results'):
            print(f"   First result: {data['results'][0].get('title', 'N/A')}")
    else:
        print(f"❌ Deep Search Failed: {response.status_code}")

def test_health():
    print("\n❤️ Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print(f"✅ Health Check: {response.json()}")
    else:
        print(f"❌ Health Check Failed: {response.status_code}")

if __name__ == "__main__":
    print("🧪 API Testing Suite for AI Web Navigator")
    print("Make sure the server is running: uvicorn app.api.server:app --reload --port 8000\n")
    
    try:
        test_health()
        test_quick_search()
        test_deep_search()
        print("\n🎊 All tests completed!")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on port 8000")
        print("Run: uvicorn app.api.server:app --reload --port 8000")