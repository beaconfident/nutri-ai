import sqlite3
import os

# Check the database in the instance folder
db_path = os.path.join('instance', 'site.db')
print(f"Checking database at: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")
print(f"Database size: {os.path.getsize(db_path) if os.path.exists(db_path) else 0} bytes")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {[table[0] for table in tables]}")
    
    # Check users table
    if 'user' in [table[0] for table in tables]:
        cursor.execute("SELECT id, username, email FROM user;")
        users = cursor.fetchall()
        print(f"Users: {users}")
        
        # Check if admin user exists
        cursor.execute("SELECT username, email FROM user WHERE username='admin';")
        admin_user = cursor.fetchone()
        print(f"Admin user: {admin_user}")
    
    conn.close()

# Also check the root database
root_db_path = 'site.db'
print(f"\nChecking database at: {root_db_path}")
print(f"Database exists: {os.path.exists(root_db_path)}")
print(f"Database size: {os.path.getsize(root_db_path) if os.path.exists(root_db_path) else 0} bytes")
