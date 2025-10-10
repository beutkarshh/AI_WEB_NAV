"""
Wikipedia Movie Scraper CLI
Command-line interface for managing long-running Wikipedia scraping jobs
"""

import argparse
import sys
import time
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.wiki.orchestrator import orchestrator

def create_job_command(args):
    """Create a new movie collection job"""
    print(f"🎬 Creating Wikipedia movie collection job...")
    print(f"   📅 Years to collect: {args.years_back} years back")
    print(f"   📦 Shard size: {args.shard_size} movies per file")
    
    job_id = orchestrator.start_movie_collection_job(
        description=args.description or f"Collect movies from last {args.years_back} years",
        years_back=args.years_back,
        shard_size=args.shard_size,
        start_immediately=args.start_now
    )
    
    print(f"✅ Job created: {job_id}")
    
    if args.start_now:
        print(f"🚀 Job started in background thread")
        print(f"💡 Use 'python -m app.wiki.cli status {job_id}' to check progress")
    else:
        print(f"⏸️  Job queued (not started)")
        print(f"💡 Use 'python -m app.wiki.cli start {job_id}' to begin processing")
    
    return job_id

def start_job_command(args):
    """Start a queued job"""
    job_id = args.job_id
    print(f"🚀 Starting job: {job_id}")
    
    success = orchestrator.start_job_processing(job_id)
    if success:
        print(f"✅ Job started successfully in background thread")
        print(f"💡 Use 'python -m app.wiki.cli status {job_id}' to check progress")
    else:
        print(f"❌ Failed to start job (may already be running or completed)")

def status_command(args):
    """Show job status and progress"""
    if args.job_id:
        # Show specific job status
        job_data = orchestrator.get_job_progress(args.job_id)
        if not job_data:
            print(f"❌ Job not found: {args.job_id}")
            return
        
        print(f"\n🎬 Job Status: {args.job_id}")
        print(f"   📝 Description: {job_data['description']}")
        print(f"   🎯 Status: {job_data['status'].upper()}")
        print(f"   📅 Created: {job_data['created_at']}")
        
        if job_data['started_at']:
            print(f"   🚀 Started: {job_data['started_at']}")
        
        if job_data['completed_at']:
            print(f"   ✅ Completed: {job_data['completed_at']}")
        
        print(f"\n📊 Progress:")
        print(f"   📈 Total items: {job_data['items_total']}")
        print(f"   ✅ Processed: {job_data['items_processed']}")
        print(f"   ❌ Failed: {job_data['items_failed']}")
        print(f"   🎯 Progress: {job_data['progress_percent']:.1f}%")
        
        if job_data['current_year']:
            print(f"   🗓️  Current year: {job_data['current_year']}")
        
        if job_data['current_page']:
            print(f"   📄 Current page: {job_data['current_page']}")
        
        if job_data['items_per_hour'] > 0:
            print(f"   ⚡ Rate: {job_data['items_per_hour']:.1f} items/hour")
        
        if job_data['last_error']:
            print(f"\n❌ Last Error: {job_data['last_error']}")
        
        # Show data folder
        print(f"\n📂 Output Location: {job_data['data_folder']}")
    
    else:
        # Show all jobs
        jobs = orchestrator.list_all_jobs()
        if not jobs:
            print("📭 No jobs found")
            return
        
        print(f"\n🎬 All Wikipedia Jobs ({len(jobs)} total):")
        print("-" * 100)
        
        for job in jobs:
            status_icon = {
                'queued': '⏸️ ',
                'running': '🏃',
                'completed': '✅',
                'failed': '❌',
                'paused': '⏸️ '
            }.get(job['status'], '❓')
            
            print(f"{status_icon} {job['job_id']}")
            print(f"    📝 {job['description']}")
            print(f"    📊 {job['items_processed']}/{job['items_total']} items ({job['progress_percent']:.1f}%)")
            print(f"    📅 Created: {job['created_at']}")
            print()

def results_command(args):
    """Show results from a completed job"""
    job_id = args.job_id
    limit = args.limit
    
    print(f"📊 Results for job: {job_id}")
    
    # Check job status first
    job_data = orchestrator.get_job_progress(job_id)
    if not job_data:
        print(f"❌ Job not found: {job_id}")
        return
    
    if job_data['status'] != 'completed':
        print(f"⚠️  Job status is '{job_data['status']}' - results may be incomplete")
    
    # Get results
    results = orchestrator.get_job_results(job_id, limit)
    
    if not results:
        print("📭 No results found")
        return
    
    print(f"\n🎬 Found {len(results)} movies (showing first {limit}):")
    print("-" * 80)
    
    for i, movie in enumerate(results, 1):
        print(f"{i:3d}. {movie['title']} ({movie['year']})")
        if movie.get('director'):
            print(f"      🎬 Director: {movie['director']}")
        if movie.get('starring'):
            starring = movie['starring'][:100] + '...' if len(movie['starring']) > 100 else movie['starring']
            print(f"      ⭐ Starring: {starring}")
        print(f"      🔗 {movie['url']}")
        print()

def watch_command(args):
    """Watch job progress in real-time"""
    job_id = args.job_id
    interval = args.interval
    
    print(f"👀 Watching job: {job_id} (updates every {interval}s)")
    print("Press Ctrl+C to stop watching")
    
    try:
        while True:
            job_data = orchestrator.get_job_progress(job_id)
            if not job_data:
                print(f"❌ Job not found: {job_id}")
                break
            
            # Clear screen and show status
            print(f"\r🎬 {job_data['status'].upper()} | "
                  f"📊 {job_data['items_processed']}/{job_data['items_total']} "
                  f"({job_data['progress_percent']:.1f}%) | "
                  f"❌ {job_data['items_failed']} failed", end='', flush=True)
            
            if job_data['status'] in ['completed', 'failed']:
                print(f"\n✅ Job finished with status: {job_data['status']}")
                break
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print(f"\n👋 Stopped watching job {job_id}")

def main():
    parser = argparse.ArgumentParser(description='Wikipedia Movie Scraper - Long Running Tasks')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create job command
    create_parser = subparsers.add_parser('create', help='Create a new movie collection job')
    create_parser.add_argument('--years-back', type=int, default=20, 
                              help='How many years back to collect (default: 20)')
    create_parser.add_argument('--shard-size', type=int, default=100,
                              help='Movies per JSONL shard file (default: 100)')
    create_parser.add_argument('--description', 
                              help='Custom job description')
    create_parser.add_argument('--no-start', dest='start_now', action='store_false',
                              help='Create job but don\'t start immediately')
    create_parser.set_defaults(func=create_job_command)
    
    # Start job command
    start_parser = subparsers.add_parser('start', help='Start a queued job')
    start_parser.add_argument('job_id', help='Job ID to start')
    start_parser.set_defaults(func=start_job_command)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show job status')
    status_parser.add_argument('job_id', nargs='?', help='Specific job ID (optional)')
    status_parser.set_defaults(func=status_command)
    
    # Results command
    results_parser = subparsers.add_parser('results', help='Show job results')
    results_parser.add_argument('job_id', help='Job ID to get results for')
    results_parser.add_argument('--limit', type=int, default=50, 
                               help='Max number of results to show (default: 50)')
    results_parser.set_defaults(func=results_command)
    
    # Watch command
    watch_parser = subparsers.add_parser('watch', help='Watch job progress in real-time')
    watch_parser.add_argument('job_id', help='Job ID to watch')
    watch_parser.add_argument('--interval', type=int, default=5,
                             help='Update interval in seconds (default: 5)')
    watch_parser.set_defaults(func=watch_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    args.func(args)

if __name__ == '__main__':
    main()