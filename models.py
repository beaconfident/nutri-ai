from database import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Health Information
    age = db.Column(db.Integer, nullable=True)
    weight = db.Column(db.Float, nullable=True)  # in kg
    height = db.Column(db.Float, nullable=True)  # in cm
    gender = db.Column(db.String(10), nullable=True)
    activity_level = db.Column(db.String(50), nullable=True)  # sedentary, light, moderate, active, very_active
    health_conditions = db.Column(db.String(200), nullable=True)  # comma-separated conditions
    dietary_restrictions = db.Column(db.String(200), nullable=True)  # comma-separated restrictions
    
    # Health Goals
    goal = db.Column(db.String(100), nullable=True)  # weight_loss, muscle_gain, maintenance
    target_weight = db.Column(db.Float, nullable=True)  # in kg
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chats = db.relationship('Chat', backref='user', lazy=True)
    
    def calculate_bmi(self):
        if not self.height or not self.weight:
            return None
        # Convert height from cm to meters
        height_m = self.height / 100
        return round(self.weight / (height_m ** 2), 1)
    
    def get_bmi_category(self):
        bmi = self.calculate_bmi()
        if not bmi:
            return "Not available"
        if bmi < 18.5:
            return "Underweight"
        elif 18.5 <= bmi < 25:
            return "Normal weight"
        elif 25 <= bmi < 30:
            return "Overweight"
        else:
            return "Obese"
    
    def get_daily_calorie_needs(self):
        if not all([self.age, self.weight, self.height, self.gender, self.activity_level]):
            return None
            
        # Basal Metabolic Rate (BMR) calculation using Mifflin-St Jeor Equation
        if self.gender.lower() == 'male':
            bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age + 5
        else:  # female
            bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age - 161
        
        # Activity level multipliers
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        
        # Adjust for goal
        goal_adjustment = 1.0
        if self.goal == 'weight_loss':
            goal_adjustment = 0.85  # 15% calorie deficit
        elif self.goal == 'muscle_gain':
            goal_adjustment = 1.15  # 15% calorie surplus
            
        return round(bmr * activity_multipliers.get(self.activity_level.lower(), 1.2) * goal_adjustment)
    chats = db.relationship("Chat", backref="user")


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_message = db.Column(db.Text)
    bot_message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

