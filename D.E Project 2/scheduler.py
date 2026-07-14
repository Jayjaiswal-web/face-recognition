"""
scheduler.py — Background APScheduler
Checks every minute if any lecture should start or end based on the timetable.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

_scheduler = None

# Day mapping for Python's datetime.weekday()
DAY_MAP = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday",
    3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
}

def check_timetable(db):
    """Called every minute. Starts/ends lecture sessions in Supabase based on schedule."""
    now = datetime.now()
    current_day  = DAY_MAP[now.weekday()]
    current_time = now.strftime("%H:%M")

    try:
        all_lectures = db.get_all_lectures()
        
        for lec in all_lectures:
            # Table row index map: 0:id, 1:subject, 2:class, 3:day, 4:start, 5:end
            lec_id, subject, class_name, day, start, end = lec

            # Normalise times to HH:MM for comparison (Postgres might return HH:MM:SS)
            start_hm = start[:5] if start else ""
            end_hm   = end[:5]   if end   else ""

            if day == current_day:
                # Check for Start Time
                if current_time == start_hm:
                    if db.start_session(lec_id):
                        print(f"[Scheduler] ✅ AUTO-START: {subject} ({class_name})")
                    else:
                        # Session might already be active
                        pass

                # Check for End Time
                if end_hm and current_time == end_hm:
                    db.end_session(lec_id)
                    print(f"[Scheduler] 🔴 AUTO-END: {subject} ({class_name})")

    except Exception as e:
        print(f"[Scheduler] ⚠️ Error during timetable check: {e}")


def start_scheduler(db):
    global _scheduler
    if _scheduler is not None:
        return  # already running

    # Clear any stale active sessions from a previous run to ensure fresh state
    print("[Scheduler] 🧹 Cleaning up stale active sessions...")
    db.clear_all_sessions()

    # Create and start the background scheduler
    # Note: Using Asia/Kolkata by default as per the user's previous code
    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(
        func=check_timetable,
        args=[db],
        trigger="cron",
        minute="*",   # execution every minute
        id="timetable_check",
        replace_existing=True
    )
    _scheduler.start()
    print("[Scheduler] 🟢 Timetable monitor started (checking every 60s)")
