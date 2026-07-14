import os
from supabase_manager import SupabaseManager

def migrate():
    manager = SupabaseManager()
    faces_dir = "faces"
    
    if not os.path.exists(faces_dir):
        print(f"❌ Folder '{faces_dir}' not found.")
        return

    print(f"🚀 Starting migration of faces in '{faces_dir}' to Supabase Storage...")
    
    files = os.listdir(faces_dir)
    image_extensions = ('.jpg', '.jpeg', '.png')
    count = 0
    
    for filename in files:
        if filename.lower().endswith(image_extensions):
            file_path = os.path.join(faces_dir, filename)
            print(f"⬆️ Uploading {filename}...")
            if manager.upload_face(file_path):
                count += 1
            else:
                print(f"⚠️ Failed to upload {filename}")
                
    print(f"\n✅ Migration finished. {count} images uploaded to Supabase Storage.")

if __name__ == "__main__":
    migrate()
