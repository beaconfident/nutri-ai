from app import app, db, User, HealthAssessment, DailyMealPlan
from werkzeug.security import generate_password_hash

def init_database():
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Creating admin user...")
            admin = User(
                username='admin',
                email='admin@nutriai.com',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
            print("Username: admin")
            print("Password: admin123")
        else:
            print("Admin user already exists.")
            
        # Verify tables
        print("\nDatabase initialization complete!")
        print("You can now run the application with: python app.py")

if __name__ == '__main__':
    init_database()
