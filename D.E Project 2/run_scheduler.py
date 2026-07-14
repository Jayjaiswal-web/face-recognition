import time
from database import DatabaseManager
from scheduler import start_scheduler

def main():
    db = DatabaseManager()
    
    print("🚀 Initializing Automated Timetable Scheduler...")
    
    # Check if we can connect to Supabase
    try:
        lectures = db.get_all_lectures()
        print(f"📡 Connected to Supabase. Monitoring {len(lectures)} lectures in timetable.")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase or fetch lectures: {e}")
        return

    # Start the background scheduler
    start_scheduler(db)

    print("\n🟢 Scheduler is active and running in the background.")
    print("⏲️  It will check for session starts/ends every minute.")
    print("⌨️  Press Ctrl+C to stop the scheduler.")

    try:
        # Keep the main thread alive so the background scheduler can run
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Scheduler stopped by user.")

if __name__ == "__main__":
    main()
