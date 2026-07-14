import os
from supabase_manager import SupabaseManager

def create_test_admin():
    sm = SupabaseManager()
    if not sm.client:
        print("Failed to initialize Supabase client.")
        return

    name = "Test Admin"
    username = "admin"
    password = "password123"
    role = "admin"

    print("Checking for existing user...")
    users = sm.get_all_users()
    for u in users:
        if u[3] == username:
            print(f"✅ User '{username}' already exists! Try logging in with your previous password.")
            return

    print(f"Creating new test admin (Username: {username}, Password: {password})...")
    user_id = sm.add_user(name=name, role=role, username=username, password=password)
    
    if user_id:
        print(f"✅ Success! Admin created. You can now login with:")
        print(f"Username: {username}")
        print(f"Password: {password}")
    else:
        print("❌ Failed to create user. Check your Supabase configuration or network connection.")

if __name__ == "__main__":
    create_test_admin()
