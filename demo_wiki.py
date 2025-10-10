"""
Wikipedia Movie Scraper Demo
Demonstrates the complete long-running task system
"""

import time
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.wiki.orchestrator import orchestrator

def run_demo():
    """Run a complete demonstration of the Wikipedia movie scraping system"""
    
    print("🎬 Wikipedia Movie Scraper - Long Running Task Demo")
    print("=" * 60)
    
    # 1. Create a job for last 5 years (small demo)
    print("\n1️⃣  Creating movie collection job...")
    job_id = orchestrator.start_movie_collection_job(
        description="Demo: Collect movies from last 5 years",
        years_back=5,
        shard_size=50,
        start_immediately=True
    )
    
    print(f"✅ Job created: {job_id}")
    print(f"📂 Data will be saved to: data/wiki_jobs/{job_id}/")
    
    # 2. Monitor progress
    print("\n2️⃣  Monitoring job progress...")
    last_processed = -1
    
    for i in range(30):  # Monitor for up to 30 iterations
        job_data = orchestrator.get_job_progress(job_id)
        if not job_data:
            print("❌ Job not found!")
            break
        
        status = job_data['status']
        processed = job_data['items_processed']
        total = job_data['items_total']
        
        # Print progress if it changed
        if processed != last_processed:
            progress = (processed / total * 100) if total > 0 else 0
            print(f"📊 Status: {status.upper()} | Progress: {processed}/{total} ({progress:.1f}%)")
            last_processed = processed
        
        # Check if completed
        if status in ['completed', 'failed']:
            break
        
        time.sleep(2)  # Check every 2 seconds
    
    # 3. Show final results
    print("\n3️⃣  Final Results:")
    final_job_data = orchestrator.get_job_progress(job_id)
    
    if final_job_data:
        print(f"   🎯 Status: {final_job_data['status'].upper()}")
        print(f"   📊 Movies processed: {final_job_data['items_processed']}")
        print(f"   ❌ Failed: {final_job_data['items_failed']}")
        print(f"   📂 Output folder: {final_job_data['data_folder']}")
        
        # Show some sample results
        if final_job_data['status'] == 'completed' and final_job_data['items_processed'] > 0:
            print("\n4️⃣  Sample Movies Found:")
            results = orchestrator.get_job_results(job_id, limit=5)
            
            for i, movie in enumerate(results[:5], 1):
                print(f"   {i}. {movie['title']} ({movie['year']})")
                if movie.get('director'):
                    print(f"      🎬 Director: {movie['director']}")
        
        # Show data structure
        print("\n5️⃣  Data Structure:")
        data_folder = Path(final_job_data['data_folder'])
        if data_folder.exists():
            print(f"   📁 {data_folder}")
            for year_folder in sorted(data_folder.iterdir()):
                if year_folder.is_dir():
                    jsonl_files = list(year_folder.glob("*.jsonl"))
                    print(f"   ├── {year_folder.name}/ ({len(jsonl_files)} JSONL files)")
                    for jsonl_file in jsonl_files[:3]:  # Show first 3 files
                        print(f"   │   ├── {jsonl_file.name}")
    
    print("\n✅ Demo completed!")
    return job_id

def show_usage_examples():
    """Show different ways to use the system"""
    print("\n🚀 Usage Examples:")
    print("-" * 40)
    
    print("\n📋 Command Line Interface:")
    print("   # Create job for last 20 years")
    print("   python -m app.wiki.cli create --years-back 20")
    print()
    print("   # Check status of specific job")
    print("   python -m app.wiki.cli status JOB_ID")
    print()
    print("   # Watch job progress in real-time")
    print("   python -m app.wiki.cli watch JOB_ID")
    print()
    print("   # Get results from completed job")
    print("   python -m app.wiki.cli results JOB_ID --limit 100")
    
    print("\n🌐 API Endpoints:")
    print("   POST /wiki/jobs - Create new job")
    print("   GET /wiki/jobs - List all jobs")
    print("   GET /wiki/jobs/{id} - Get job status")
    print("   GET /wiki/jobs/{id}/results - Get job results")
    
    print("\n📁 Output Structure:")
    print("   data/wiki_jobs/{job_id}/")
    print("   ├── 2023/")
    print("   │   ├── part_001.jsonl")
    print("   │   ├── part_002.jsonl")
    print("   │   └── ...")
    print("   ├── 2024/")
    print("   │   └── part_001.jsonl")
    print("   └── ...")

if __name__ == "__main__":
    # Run the demo
    job_id = run_demo()
    
    # Show usage examples
    show_usage_examples()
    
    print(f"\n💡 Your demo job ID: {job_id}")
    print(f"💡 Try: python -m app.wiki.cli status {job_id}")