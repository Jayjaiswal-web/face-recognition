import cv2
import numpy as np
from deepface import DeepFace
from database import DatabaseManager
import os
import time

def run_attendance_cam():
    db = DatabaseManager()
    
    # 1. Sync faces from Supabase Storage locally
    print("🔄 Syncing face data from Supabase Storage...")
    db.sync_faces_local()
    
    faces_dir = "faces"
    if not os.path.exists(faces_dir) or not os.listdir(faces_dir):
        print("❌ No face data found. Register a face first!")
        return

    # 2. Identify the active lecture
    active_lec = db.get_first_active_lecture()
    if not active_lec:
        print("⚠️ No active lecture session found in Supabase.")
        print("💡 Tip: Start a session in the Supabase 'active_sessions' table to log attendance.")
        lecture_id = None
        lecture_subject = "None (Monitoring Only)"
    else:
        lecture_id, lecture_subject = active_lec
        print(f"📡 System ready. Logging attendance for: {lecture_subject}")

    # 3. Initialize Camera
    cap = cv2.VideoCapture(0)
    process_this_frame = 0
    
    print("🟢 Camera started. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        process_this_frame += 1

        # Only run recognition every 3 frames for performance
        if process_this_frame % 3 == 0:
            try:
                # DeepFace.find searches the local faces/ directory
                # Using detector_backend="opencv" for speed, or "mediapipe" if available
                results = DeepFace.find(
                    img_path=frame,
                    db_path=faces_dir,
                    detector_backend="opencv",
                    enforce_detection=False,
                    silent=True
                )
                
                if len(results) > 0 and not results[0].empty:
                    match = results[0].iloc[0]
                    # Format: id_name_count.jpg
                    filename = os.path.basename(match['identity'])
                    user_id = filename.split('_')[0]
                    
                    # Get user name (from filename or DB)
                    user_name = db.get_user_name_by_id(user_id)
                    
                    # Draw on frame
                    # The results dataframe contains box coordinates in newer versions
                    # but for simplicity we draw around the detection
                    x, y, w, h = int(match['source_x']), int(match['source_y']), int(match['source_w']), int(match['source_h'])
                    
                    # LOG ATTENDANCE TO SUPABASE
                    if lecture_id:
                        if db.mark_attendance(user_id, lecture_id):
                            print(f"✅ Attendance Logged: {user_name} for {lecture_subject}")
                            color = (0, 255, 0) # Green for success
                        else:
                            color = (0, 255, 255) # Yellow for already logged
                    else:
                        color = (0, 200, 255) # Light blue for monitor only

                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
                    cv2.putText(frame, user_name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)
            except Exception as e:
                # Detection might fail if no face is in frame
                pass

        cv2.putText(frame, f"Lecture: {lecture_subject}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imshow('Face Attendance - Supabase Sync', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_attendance_cam()
