import os
import sqlite3
from datetime import datetime

# Create instance directory if it doesn't exist
instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
if not os.path.exists(instance_dir):
    os.makedirs(instance_dir)

# Database path
db_path = os.path.join(instance_dir, 'site.db')

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    date_created DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS health_assessment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    height REAL NOT NULL,
    weight REAL NOT NULL,
    activity_level TEXT NOT NULL,
    health_goal TEXT NOT NULL,
    dietary_restrictions TEXT,
    bmi REAL NOT NULL,
    daily_calories REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS daily_meal_plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL,
    date DATE NOT NULL,
    meals TEXT NOT NULL,
    total_calories REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assessment_id) REFERENCES health_assessment (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    user_message TEXT NOT NULL,
    bot_message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user (id)
)
''')

# Commit and close
conn.commit()
conn.close()

print("Database created successfully!")
print(f"Database location: {db_path}")
