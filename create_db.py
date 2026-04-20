#!/usr/bin/env python3

import os
os.environ['FLASK_APP'] = 'app.py'

from app import app, db

def create_database():
    """Create database with all tables"""
    with app.app_context():
        # Drop all existing tables
        db.drop_all()
        print("Dropped all existing tables")
        
        # Create all tables
        db.create_all()
        print("Created all tables")
        
        # Verify tables were created
        import sqlite3
        conn = sqlite3.connect('site.db')
        cursor = conn.cursor()
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables in database: {[table[0] for table in tables]}")
        
        # Check health_assessment table structure
        if ('health_assessment',) in tables:
            cursor.execute("PRAGMA table_info(health_assessment)")
            columns = cursor.fetchall()
            print("\nHealth assessment table columns:")
            for col in columns:
                print(f"  - {col[1]}: {col[2]} {'(NULL)' if col[3] == 0 else '(NOT NULL)'}")
        
        conn.close()

if __name__ == '__main__':
    create_database()
