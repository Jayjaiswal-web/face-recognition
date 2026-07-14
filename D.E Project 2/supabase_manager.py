import os
from supabase import create_client, Client
from dotenv import load_dotenv
import hashlib
from datetime import datetime

# Load environment variables from .env
load_dotenv()

class SupabaseManager:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            print("⚠️ Warning: SUPABASE_URL or SUPABASE_KEY not found in .env file.")
            self.client = None
            self.storage = None
        else:
            self.client: Client = create_client(url, key)
            self.storage = self.client.storage.from_("faces")

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    # ── Auth ──────────────────────────────────────────────────────────────────

    def authenticate(self, username, password):
        if not self.client: return None
        hashed = self.hash_password(password)
        try:
            response = self.client.table("users").select("id, name, role").eq("username", username).eq("password", hashed).execute()
            if response.data:
                user = response.data[0]
                return (user["id"], user["name"], user["role"])
            return None
        except Exception as e:
            print(f"Auth error: {e}")
            return None

    def get_user_by_id(self, user_id):
        if not self.client: return None
        try:
            response = self.client.table("users").select("id, name, role, username, class_id").eq("id", user_id).execute()
            if response.data:
                u = response.data[0]
                return (u["id"], u["name"], u["role"], u["username"], u["class_id"])
            return None
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None

    def get_user_name_by_id(self, user_id):
        """Helper to get just the user name by ID."""
        user = self.get_user_by_id(user_id)
        if user:
            return user[1] # name is at index 1
        return "Unknown"

    # ── Users ─────────────────────────────────────────────────────────────────

    def add_user(self, name, role='student', username=None, password=None, class_id=None):
        if not self.client: return None
        hashed = self.hash_password(password) if password else None
        data = {
            "name": name,
            "role": role,
            "username": username,
            "password": hashed,
            "class_id": class_id
        }
        try:
            response = self.client.table("users").insert(data).execute()
            if response.data:
                return response.data[0]["id"]
            return None
        except Exception as e:
            print(f"Error adding user: {e}")
            return None

    def get_all_users(self):
        if not self.client: return []
        try:
            # Joining classes table via foreign key
            response = self.client.table("users").select("id, name, role, username, classes(name)").execute()
            result = []
            for u in response.data:
                class_name = u["classes"]["name"] if u.get("classes") else None
                result.append((u["id"], u["name"], u["role"], u["username"], class_name))
            return result
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []

    # ── Classes ───────────────────────────────────────────────────────────────

    def add_class(self, name):
        if not self.client: return None
        try:
            response = self.client.table("classes").insert({"name": name}).execute()
            if response.data:
                return response.data[0]["id"]
            return None
        except Exception as e:
            print(f"Error adding class: {e}")
            return None

    def get_all_classes(self):
        if not self.client: return []
        try:
            response = self.client.table("classes").select("id, name").order("name").execute()
            return [(c["id"], c["name"]) for c in response.data]
        except Exception as e:
            print(f"Error fetching classes: {e}")
            return []

    # ── Lectures ──────────────────────────────────────────────────────────────

    def add_lecture(self, subject, class_id, day_of_week, start_time, end_time):
        if not self.client: return None
        data = {
            "subject": subject,
            "class_id": class_id,
            "day_of_week": day_of_week,
            "start_time": start_time,
            "end_time": end_time
        }
        try:
            response = self.client.table("lectures").insert(data).execute()
            return response.data is not None
        except Exception as e:
            print(f"Error adding lecture: {e}")
            return False

    def get_all_lectures(self):
        if not self.client: return []
        try:
            response = self.client.table("lectures").select("id, subject, day_of_week, start_time, end_time, classes(name)").execute()
            result = []
            for l in response.data:
                class_name = l["classes"]["name"] if l.get("classes") else "Unknown"
                result.append((l["id"], l["subject"], class_name, l["day_of_week"], l["start_time"], l["end_time"]))
            return result
        except Exception as e:
            print(f"Error fetching lectures: {e}")
            return []

    # ── Attendance ────────────────────────────────────────────────────────────

    def mark_attendance(self, user_id, lecture_id):
        if not self.client: return False
        data = {
            "user_id": user_id,
            "lecture_id": lecture_id,
            # date and time are defaulted in DB schema
        }
        try:
            # Supabase insert will fail on unique constraint if already marked (date, user, lecture)
            response = self.client.table("attendance").insert(data).execute()
            return response.data is not None
        except Exception as e:
            # Likely integrity error (duplicate attendance for same day)
            print(f"Attendance mark skip or error: {e}")
            return False

    def get_attendance_by_user(self, user_id):
        """Fetch all attendance records for a single student across all lectures."""
        if not self.client: return []
        try:
            response = self.client.table("attendance") \
                .select("date, time, lecture_id, lectures(subject, day_of_week, start_time, end_time, classes(name))") \
                .eq("user_id", user_id) \
                .order("date", desc=True) \
                .execute()
            result = []
            for r in response.data:
                lec = r.get("lectures") or {}
                class_name = (lec.get("classes") or {}).get("name", "Unknown")
                result.append({
                    "date": str(r["date"]),
                    "time": str(r["time"]),
                    "lecture_id": r["lecture_id"],
                    "subject": lec.get("subject", "Unknown"),
                    "class_name": class_name,
                    "day_of_week": lec.get("day_of_week", ""),
                    "start_time": (lec.get("start_time") or "")[:5],
                    "end_time": (lec.get("end_time") or "")[:5],
                })
            return result
        except Exception as e:
            print(f"Error fetching user attendance: {e}")
            return []

    def get_attendance_by_lecture(self, lecture_id, date=None):
        if not self.client: return []
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        try:
            response = self.client.table("attendance") \
                .select("users(name), time, user_id") \
                .eq("lecture_id", lecture_id) \
                .eq("date", date) \
                .order("time", desc=True) \
                .execute()
            result = []
            for r in response.data:
                name = r["users"]["name"] if r.get("users") else "Unknown"
                result.append((name, r["time"], r["user_id"]))
            return result
        except Exception as e:
            print(f"Error fetching attendance: {e}")
            return []

    # ── Active Sessions ───────────────────────────────────────────────────────

    def start_session(self, lecture_id):
        if not self.client: return False
        try:
            # upsert to avoid duplicates
            response = self.client.table("active_sessions").upsert({"lecture_id": lecture_id}).execute()
            return response.data is not None
        except Exception as e:
            print(f"Error starting session: {e}")
            return False

    def end_session(self, lecture_id):
        if not self.client: return False
        try:
            self.client.table("active_sessions").delete().eq("lecture_id", lecture_id).execute()
        except Exception as e:
            print(f"Error ending session: {e}")

    def clear_all_sessions(self):
        if not self.client: return
        try:
            # Delete all (NEQ dummy or just delete all if filter allowed)
            self.client.table("active_sessions").delete().neq("lecture_id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception as e:
            print(f"Error clearing sessions: {e}")

    def get_first_active_lecture(self):
        """Returns the ID and subject of the first currently active lecture."""
        if not self.client: return None
        try:
            response = self.client.table("active_sessions").select("lecture_id, lectures(subject)").limit(1).execute()
            if response.data:
                item = response.data[0]
                return (item["lecture_id"], item["lectures"]["subject"])
            return None
        except Exception as e:
            print(f"Error fetching active lecture: {e}")
            return None

    def get_active_sessions(self):
        """Return all currently active lecture sessions with full info."""
        if not self.client: return []
        try:
            response = self.client.table("active_sessions") \
                .select("lecture_id, started_at, lectures(subject, class_id, day_of_week, start_time, end_time, classes(name))") \
                .order("started_at", desc=True) \
                .execute()
            
            result = []
            for item in response.data:
                lec = item["lectures"]
                class_name = lec["classes"]["name"] if lec.get("classes") else "Unknown"
                result.append((
                    item["lecture_id"],
                    lec["subject"],
                    class_name,
                    lec["day_of_week"],
                    lec["start_time"],
                    lec["end_time"],
                    item["started_at"]
                ))
            return result
        except Exception as e:
            print(f"Error fetching active sessions: {e}")
            return []

    # ── Storage ───────────────────────────────────────────────────────────────

    def upload_face(self, file_path):
        """Uploads a local image file to the 'faces' bucket."""
        if not self.storage: return False
        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'rb') as f:
                self.storage.upload(path=filename, file=f, file_options={"upsert": "true"})
            return True
        except Exception as e:
            print(f"Storage upload error ({filename}): {e}")
            return False

    def sync_faces_local(self, local_dir="faces"):
        """Downloads all images from Supabase Storage to the local directory."""
        if not self.storage: return
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
            
        try:
            files = self.storage.list()
            for file_info in files:
                name = file_info['name']
                if name == ".emptyFolderPlaceholder": continue
                
                local_path = os.path.join(local_dir, name)
                # Skip if already exists (basic optimization)
                if os.path.exists(local_path): continue
                
                print(f"📥 Syncing {name}...")
                with open(local_path, 'wb') as f:
                    data = self.storage.download(name)
                    f.write(data)
            print("✅ Face synchronization complete.")
        except Exception as e:
            print(f"Sync error: {e}")

def test_connection():
    manager = SupabaseManager()
    if manager.client:
        print("✅ Supabase Client initialized successfully.")
        try:
            # Try a simple select to verify keys
            manager.client.table("classes").select("count", count="exact").execute()
            print("✅ Connection verified: Successfully queried 'classes' table.")
        except Exception as e:
            print(f"❌ Connection check failed: {e}")
    else:
        print("❌ Supabase Client failed to initialize. Check your .env file.")

if __name__ == "__main__":
    test_connection()
