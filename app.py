# Import statements and dependencies

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import random
import json
import io
from sqlalchemy import func
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from chatbot import ai_chatbot_response
from types import SimpleNamespace


# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "GROQ_API_KEY"
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'site.db')
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
print(f"[DEBUG] Using database file: {db_path}")

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    dietary_restrictions = db.Column(db.Text, nullable=True)
    health_conditions = db.Column(db.Text, nullable=True)
    profile_image = db.Column(db.String(200), default='images/profile-placeholder.png')
    health_assessments = db.relationship('HealthAssessment', backref='user', lazy=True)
    chats = db.relationship('Chat', backref='user', lazy=True)

class HealthAssessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    age = db.Column(db.Integer)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    gender = db.Column(db.String(20))
    activity_level = db.Column(db.String(50))
    goal = db.Column(db.String(50))
    bmi = db.Column(db.Float)
    bmi_category = db.Column(db.String(50))
    daily_calories = db.Column(db.Float)
    target_weight = db.Column(db.Float)
    expected_weeks = db.Column(db.Integer)
    status = db.Column(db.String(20), default='active')
    disease_type = db.Column(db.String(50), default='None')
    allergies = db.Column(db.Text, nullable=True)
    preferred_cuisine = db.Column(db.String(50), nullable=True)
    daily_plans = db.relationship('DailyMealPlan', backref='assessment', lazy=True)

class DailyMealPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('health_assessment.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    meals = db.Column(db.JSON)
    completed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Helper Functions
def get_diet_recommendation(age, weight, height, bmi, disease_type, activity_level, goal, gender, preferred_cuisine=None, allergies=None):
    try:
        import pandas as pd
        
        # Read the dataset
        df = pd.read_csv('diet_recommendations_dataset.csv')
        
        # Filter based on health condition if specified
        if disease_type and disease_type.lower() != 'none':
            df = df[df['Disease_Type'].str.lower() == disease_type.lower()]
        
        # Calculate BMI category
        if bmi < 18.5:
            bmi_category = "Underweight"
        elif 18.5 <= bmi < 25:
            bmi_category = "Normal weight"
        elif 25 <= bmi < 30:
            bmi_category = "Overweight"
        else:
            bmi_category = "Obese"
        
        # Filter by activity level
        activity_map = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        
        # Filter by gender
        if gender and gender.lower() in ['male', 'female']:
            df = df[df['Gender'].str.lower() == gender.lower()]
        
        # Filter by activity level if specified
        if activity_level and activity_level.lower() in activity_map:
            df = df[df['Physical_Activity_Level'] == activity_map[activity_level.lower()]]
        
        # Filter by preferred cuisine if specified
        if preferred_cuisine and preferred_cuisine.lower() != 'any':
            df = df[df['Preferred_Cuisine'].str.lower() == preferred_cuisine.lower()]
        
        # Determine diet recommendation type based on filtered data
        if not df.empty:
            # Get the most common diet recommendation from filtered data
            diet_type = df['Diet_Recommendation'].mode().iloc[0] if not df['Diet_Recommendation'].mode().empty else 'Balanced'
        else:
            # Default to Balanced if no matching records
            diet_type = 'Balanced'
        
        # Adjust diet type based on disease if specified
        if disease_type and disease_type.lower() != 'none':
            if disease_type.lower() == 'diabetes':
                diet_type = 'Low_Carb'
            elif disease_type.lower() == 'hypertension':
                diet_type = 'Low_Sodium'
        
        # Get dietary restrictions and preferred cuisine from filtered data
        dietary_restrictions = None
        preferred_cuisine_from_data = None
        
        if not df.empty:
            # Get most common dietary restrictions from filtered data
            restrictions_mode = df['Dietary_Restrictions'].mode()
            if not restrictions_mode.empty and restrictions_mode.iloc[0] != 'None':
                dietary_restrictions = restrictions_mode.iloc[0]
            
            # Get most common preferred cuisine from filtered data
            cuisine_mode = df['Preferred_Cuisine'].mode()
            if not cuisine_mode.empty and cuisine_mode.iloc[0] != 'Mixed':
                preferred_cuisine_from_data = cuisine_mode.iloc[0]
        
        # Use user's preferred cuisine if provided, otherwise use from dataset
        final_cuisine = preferred_cuisine if preferred_cuisine and preferred_cuisine.lower() != 'any' else preferred_cuisine_from_data
        
        # Meal databases (expanded for more variety)
        MEAL_DATABASE = {
            'Balanced': {
                'breakfast': [
                    'Oatmeal with berries and nuts', 'Greek yogurt with honey', 'Whole wheat toast with avocado', 
                    'Scrambled eggs with spinach', 'Smoothie bowl with granola', 'Cottage cheese with fruit',
                    'Whole grain pancakes', 'Breakfast burrito with vegetables', 'Quinoa porridge with cinnamon',
                    'Yogurt parfait with layers'
                ],
                'lunch': [
                    'Grilled chicken salad', 'Quinoa bowl with vegetables', 'Turkey sandwich with whole wheat bread', 
                    'Lentil soup with whole grain bread', 'Mediterranean wrap', 'Brown rice with roasted vegetables',
                    'Tuna salad with light dressing', 'Vegetable stir-fry with tofu', 'Chicken and vegetable skewers',
                    'Pasta salad with olive oil dressing'
                ],
                'dinner': [
                    'Baked salmon with sweet potato', 'Grilled chicken with quinoa', 'Vegetable stir-fry with tofu', 
                    'Pasta with tomato sauce and vegetables', 'Lean beef with broccoli', 'Fish with roasted vegetables',
                    'Chicken curry with brown rice', 'Vegetable lasagna', 'Stir-fried shrimp with vegetables',
                    'Turkey meatballs with whole wheat pasta'
                ],
                'snacks': [
                    'Apple slices with almond butter', 'Greek yogurt', 'Mixed nuts', 'Hummus with vegetable sticks',
                    'Berries with cottage cheese', 'Whole grain crackers with cheese', 'Hard-boiled eggs',
                    'Vegetable soup', 'Protein smoothie', 'Dark chocolate squares'
                ]
            },
            'Low_Carb': {
                'breakfast': [
                    'Eggs with avocado', 'Greek yogurt with berries', 'Almond flour pancakes', 'Bacon with eggs',
                    'Spinach and feta omelet', 'Chia seed pudding', 'Avocado smoothie', 'Coconut flour muffins',
                    'Sausage and cheese scramble', 'Cauliflower hash browns'
                ],
                'lunch': [
                    'Grilled chicken salad', 'Cauliflower rice bowl', 'Zucchini noodles with meat sauce', 'Tuna salad with lettuce wraps',
                    'Egg salad with avocado', 'Turkey and cheese roll-ups', 'Shrimp stir-fry', 'Beef and vegetable stir-fry',
                    'Chicken Caesar salad', 'Salmon with asparagus'
                ],
                'dinner': [
                    'Grilled salmon with asparagus', 'Steak with roasted vegetables', 'Chicken stir-fry with low-carb vegetables', 'Fish with cauliflower mash',
                    'Baked chicken with herbs', 'Pork chops with green beans', 'Lamb with roasted vegetables', 'Shrimp scampi',
                    'Beef stir-fry', 'Turkey meatballs with zucchini noodles'
                ],
                'snacks': [
                    'Cheese slices', 'Nuts and seeds', 'Vegetable sticks with guacamole', 'Hard-boiled eggs',
                    'Pork rinds', 'Olives', 'Pickles', 'Beef jerky', 'Celery with cream cheese', 'Berries with cream'
                ]
            },
            'Low_Sodium': {
                'breakfast': [
                    'Oatmeal with fresh fruit', 'Greek yogurt with honey', 'Whole wheat toast with banana', 'Scrambled eggs with herbs',
                    'Fresh fruit salad', 'Whole grain cereal with milk', 'Smoothie with fresh berries', 'Almond butter on toast',
                    'Cottage cheese with peaches', 'Yogurt with granola'
                ],
                'lunch': [
                    'Fresh vegetable salad', 'Grilled chicken with herbs', 'Lentil soup (no salt)', 'Brown rice with steamed vegetables',
                    'Quinoa salad with lemon dressing', 'Turkey and avocado wrap', 'Vegetable soup with herbs', 'Grilled fish with lemon',
                    'Bean salad with herbs', 'Pasta with fresh vegetables'
                ],
                'dinner': [
                    'Baked fish with herbs', 'Grilled chicken with vegetables', 'Vegetable curry (no salt)', 'Pasta with fresh tomato sauce',
                    'Roasted vegetables with herbs', 'Grilled turkey with sweet potato', 'Steamed fish with ginger', 'Vegetable stir-fry',
                    'Chicken with lemon and herbs', 'Brown rice with vegetables'
                ],
                'snacks': [
                    'Fresh fruit', 'Unsalted nuts', 'Yogurt with berries', 'Vegetable sticks',
                    'Rice cakes', 'Fresh vegetables', 'Dried fruit', 'Homemade trail mix', 'Fresh melon', 'Berries'
                ]
            },
            'High_Protein': {
                'breakfast': [
                    'Protein smoothie', 'Eggs with turkey bacon', 'Greek yogurt with protein powder', 'Cottage cheese with fruit',
                    'Protein pancakes', 'Egg white omelet', 'Protein oatmeal', 'Greek yogurt parfait',
                    'Scrambled eggs with cheese', 'Protein muffins'
                ],
                'lunch': [
                    'Grilled chicken breast', 'Tuna salad', 'Lean beef with vegetables', 'Salmon with quinoa',
                    'Turkey and cheese sandwich', 'Protein bowl with quinoa', 'Chicken salad sandwich', 'Tuna wrap',
                    'Lean beef salad', 'Shrimp with brown rice'
                ],
                'dinner': [
                    'Grilled steak', 'Baked chicken breast', 'Fish with vegetables', 'Lean pork with sweet potato',
                    'Protein stir-fry', 'Baked salmon with vegetables', 'Lean beef with quinoa', 'Chicken with brown rice',
                    'Turkey with roasted vegetables', 'Fish with sweet potato'
                ],
                'snacks': [
                    'Protein bars', 'Hard-boiled eggs', 'Greek yogurt', 'Protein shake',
                    'Cottage cheese', 'Almonds', 'Protein cookies', 'Beef jerky',
                    'Protein pudding', 'Edamame'
                ]
            }
        }
        
        # Cuisine-specific meals
        CUISINE_MEALS = {
            'Mexican': {
                'breakfast': ['Huevos rancheros', 'Avocado toast with jalapeños', 'Mexican breakfast bowl', 'Chilaquiles'],
                'lunch': ['Chicken tacos', 'Burrito bowl', 'Mexican salad', 'Quesadilla with vegetables'],
                'dinner': ['Chicken enchiladas', 'Beef fajitas', 'Fish tacos', 'Vegetarian chili'],
                'snacks': ['Guacamole with chips', 'Mexican fruit salad', 'Jicama sticks', 'Corn tortilla with cheese']
            },
            'Chinese': {
                'breakfast': ['Congee with vegetables', 'Chinese steamed eggs', 'Soy milk with tofu', 'Dim sum'],
                'lunch': ['Stir-fried vegetables', 'Chicken with broccoli', 'Beef with snow peas', 'Tofu stir-fry'],
                'dinner': ['Sweet and sour chicken', 'Kung pao chicken', 'Vegetable fried rice', 'Fish with ginger'],
                'snacks': ['Spring rolls', 'Edamame', 'Chinese fruit salad', 'Seaweed snacks']
            },
            'Italian': {
                'breakfast': ['Italian breakfast pastry', 'Cappuccino with biscotti', 'Fruit salad', 'Yogurt with granola'],
                'lunch': ['Caprese salad', 'Pasta primavera', 'Minestrone soup', 'Italian sandwich'],
                'dinner': ['Spaghetti carbonara', 'Chicken parmigiana', 'Risotto', 'Fish with herbs'],
                'snacks': ['Bruschetta', 'Italian olives', 'Fruit', 'Cheese and crackers']
            },
            'Indian': {
                'breakfast': ['Masala oats', 'Vegetable upma', 'Idli with sambar', 'Paratha with yogurt'],
                'lunch': ['Dal with rice', 'Chicken curry', 'Vegetable biryani', 'Palak paneer'],
                'dinner': ['Butter chicken', 'Lamb curry', 'Vegetable curry', 'Fish curry'],
                'snacks': ['Samosa', 'Pakora', 'Fruit chaat', 'Yogurt with fruits']
            },
            'American': {
                'breakfast': ['Pancakes with syrup', 'French toast', 'Bagel with cream cheese', 'Cereal with milk'],
                'lunch': ['Club sandwich', 'Burger with salad', 'Mac and cheese', 'Grilled cheese sandwich'],
                'dinner': ['Steak with potatoes', 'Fried chicken', 'Meatloaf', 'Fish and chips'],
                'snacks': ['Potato chips', 'Cookies', 'Fruit', 'Yogurt']
            },
            'Mediterranean': {
                'breakfast': ['Greek yogurt with honey', 'Hummus with pita', 'Feta cheese with olives', 'Mediterranean omelet'],
                'lunch': ['Greek salad', 'Falafel wrap', 'Lentil soup', 'Grilled fish with vegetables'],
                'dinner': ['Moussaka', 'Grilled lamb', 'Seafood pasta', 'Vegetable tagine'],
                'snacks': ['Olives', 'Feta cheese', 'Dried fruits', 'Nuts']
            },
            'Thai': {
                'breakfast': ['Thai congee', 'Coconut rice', 'Thai omelet', 'Fruit with coconut'],
                'lunch': ['Pad thai', 'Tom yum soup', 'Green curry', 'Papaya salad'],
                'dinner': ['Red curry', 'Massaman curry', 'Stir-fried vegetables', 'Grilled fish'],
                'snacks': ['Spring rolls', 'Mango sticky rice', 'Thai fruits', 'Coconut snacks']
            },
            'Japanese': {
                'breakfast': ['Miso soup with rice', 'Tamago kake gohan', 'Natto with rice', 'Japanese breakfast set'],
                'lunch': ['Sushi bowl', 'Ramen', 'Tempura', 'Bento box'],
                'dinner': ['Sushi and sashimi', 'Teriyaki chicken', 'Sukiyaki', 'Grilled fish'],
                'snacks': ['Edamame', 'Mochi', 'Japanese fruits', 'Seaweed snacks']
            }
        }
        
        def get_cuisine_specific_meals(cuisine, dietary_restrictions=None):
            if not cuisine or cuisine == 'Any':
                return {}
            
            cuisine_meals = CUISINE_MEALS.get(cuisine, {})
            
            # Apply dietary restrictions if specified
            if dietary_restrictions and dietary_restrictions != 'None':
                if dietary_restrictions.lower() == 'vegetarian':
                    # Remove meat items for vegetarian
                    for meal_type in cuisine_meals:
                        cuisine_meals[meal_type] = [meal for meal in cuisine_meals[meal_type] 
                                                  if not any(meat in meal.lower() for meat in ['chicken', 'beef', 'pork', 'lamb', 'fish', 'seafood'])]
                elif dietary_restrictions.lower() == 'vegan':
                    # Remove all animal products for vegan
                    for meal_type in cuisine_meals:
                        cuisine_meals[meal_type] = [meal for meal in cuisine_meals[meal_type] 
                                                  if not any(item in meal.lower() for item in ['chicken', 'beef', 'pork', 'lamb', 'fish', 'seafood', 'milk', 'cheese', 'yogurt', 'egg'])]
                elif dietary_restrictions.lower() == 'gluten-free':
                    # Remove gluten-containing items
                    for meal_type in cuisine_meals:
                        cuisine_meals[meal_type] = [meal for meal in cuisine_meals[meal_type] 
                                                  if not any(item in meal.lower() for item in ['bread', 'pasta', 'wheat', 'flour'])]
            
            return cuisine_meals
        
        def filter_meals_by_restriction(meals, restriction):
            if not restriction or restriction == 'None':
                return meals
            
            filtered_meals = []
            for meal in meals:
                meal_lower = meal.lower()
                if restriction.lower() == 'vegetarian':
                    if not any(meat in meal_lower for meat in ['chicken', 'beef', 'pork', 'lamb', 'fish', 'seafood']):
                        filtered_meals.append(meal)
                elif restriction.lower() == 'vegan':
                    if not any(item in meal_lower for item in ['chicken', 'beef', 'pork', 'lamb', 'fish', 'seafood', 'milk', 'cheese', 'yogurt', 'egg']):
                        filtered_meals.append(meal)
                elif restriction.lower() == 'gluten-free':
                    if not any(item in meal_lower for item in ['bread', 'pasta', 'wheat', 'flour']):
                        filtered_meals.append(meal)
                else:
                    filtered_meals.append(meal)
            
            return filtered_meals
        
        def filter_meals_by_allergies(meals, allergies):
            if not allergies:
                return meals
            
            filtered_meals = []
            allergy_list = [allergy.strip().lower() for allergy in allergies.split(',')]
            
            for meal in meals:
                meal_lower = meal.lower()
                contains_allergen = False
                
                for allergy in allergy_list:
                    if allergy in meal_lower:
                        contains_allergen = True
                        break
                
                if not contains_allergen:
                    filtered_meals.append(meal)
            
            return filtered_meals
        
        # Get meal recommendations from database with cuisine and restriction filtering
        meal_plan = {
            'breakfast': [],
            'lunch': [],
            'dinner': [],
            'snacks': [],
            'water_intake': '3L' if activity_level.lower() in ['active', 'very_active'] else '2.5L',
            'nutritional_info': {
                'target_calories': round(weight * 30 if activity_level.lower() in ['active', 'very_active'] else weight * 25),
                'protein_g': round(weight * 1.6 if goal == 'muscle_gain' else weight * 1.2),
                'carbs_g': 0,
                'fats_g': 0,
                'fiber_g': 30
            },
            'notes': []
        }
        
        # Get cuisine-specific meals
        cuisine_meals = get_cuisine_specific_meals(final_cuisine, dietary_restrictions)
        
        # Combine with diet type meals for variety
        if diet_type in MEAL_DATABASE:
            # If user explicitly selected a specific cuisine (not 'Any'), use cuisine meals only
            if final_cuisine and str(final_cuisine).lower() != 'any' and final_cuisine in CUISINE_MEALS:
                all_breakfast = cuisine_meals.get('breakfast', []) or MEAL_DATABASE[diet_type]['breakfast']
                all_lunch = cuisine_meals.get('lunch', []) or MEAL_DATABASE[diet_type]['lunch']
                all_dinner = cuisine_meals.get('dinner', []) or MEAL_DATABASE[diet_type]['dinner']
                all_snacks = cuisine_meals.get('snacks', []) or MEAL_DATABASE[diet_type]['snacks']
            else:
                # Mix general diet meals with cuisine-specific meals
                all_breakfast = MEAL_DATABASE[diet_type]['breakfast'] + cuisine_meals.get('breakfast', [])
                all_lunch = MEAL_DATABASE[diet_type]['lunch'] + cuisine_meals.get('lunch', [])
                all_dinner = MEAL_DATABASE[diet_type]['dinner'] + cuisine_meals.get('dinner', [])
                all_snacks = MEAL_DATABASE[diet_type]['snacks'] + cuisine_meals.get('snacks', [])
            
            # Apply dietary restrictions filter
            if dietary_restrictions and dietary_restrictions != 'None':
                all_breakfast = filter_meals_by_restriction(all_breakfast, dietary_restrictions)
                all_lunch = filter_meals_by_restriction(all_lunch, dietary_restrictions)
                all_dinner = filter_meals_by_restriction(all_dinner, dietary_restrictions)
                all_snacks = filter_meals_by_restriction(all_snacks, dietary_restrictions)
            
            # Apply allergies filter
            if allergies:
                all_breakfast = filter_meals_by_allergies(all_breakfast, allergies)
                all_lunch = filter_meals_by_allergies(all_lunch, allergies)
                all_dinner = filter_meals_by_allergies(all_dinner, allergies)
                all_snacks = filter_meals_by_allergies(all_snacks, allergies)
            
            # Randomly select meals to provide variety (increased for 7-day plan)
            meal_plan['breakfast'] = random.sample(all_breakfast, min(7, len(all_breakfast)))
            meal_plan['lunch'] = random.sample(all_lunch, min(7, len(all_lunch)))
            meal_plan['dinner'] = random.sample(all_dinner, min(7, len(all_dinner)))
            meal_plan['snacks'] = random.sample(all_snacks, min(7, len(all_snacks)))
        
        # Add health-specific notes
        if disease_type and disease_type.lower() != 'none':
            meal_plan['notes'].append(f"Meal plan tailored for {disease_type} condition.")
        
        # Add goal-specific notes
        if goal == 'weight_loss':
            meal_plan['nutritional_info']['target_calories'] = round(meal_plan['nutritional_info']['target_calories'] * 0.85)
            meal_plan['notes'].append("Calorie deficit plan for healthy weight loss.")
        elif goal == 'muscle_gain':
            meal_plan['nutritional_info']['target_calories'] = round(meal_plan['nutritional_info']['target_calories'] * 1.15)
            meal_plan['notes'].append("High-protein diet to support muscle growth.")
        
        # Calculate carbs and fats based on target calories
        protein_calories = meal_plan['nutritional_info']['protein_g'] * 4
        remaining_calories = meal_plan['nutritional_info']['target_calories'] - protein_calories
        meal_plan['nutritional_info']['carbs_g'] = round((remaining_calories * 0.5) / 4)  # 50% of remaining calories from carbs
        meal_plan['nutritional_info']['fats_g'] = round((remaining_calories * 0.5) / 9)   # 50% of remaining calories from fats
        
        # Add portion sizes based on calorie needs
        portion_size = 'medium'
        if meal_plan['nutritional_info']['target_calories'] < 1800:
            portion_size = 'small'
        elif meal_plan['nutritional_info']['target_calories'] > 2500:
            portion_size = 'large'
            
        # Add portion information to meals
        for meal_type in ['breakfast', 'lunch', 'dinner']:
            meal_plan[meal_type] = [f"{meal} ({portion_size} portion)" for meal in meal_plan[meal_type]]
            
        # Add timing recommendations
        meal_plan['meal_timing'] = {
            'breakfast': 'Within 1 hour of waking',
            'snack_am': 'Mid-morning',
            'lunch': '4-5 hours after breakfast',
            'snack_pm': 'Mid-afternoon',
            'dinner': 'At least 2-3 hours before bedtime'
        }
        
        # Add final notes
        if not meal_plan['notes']:
            meal_plan['notes'].append('Maintain a balanced diet with a variety of foods.')
            
        meal_plan['notes'].extend([
            f"Target daily water intake: {meal_plan['water_intake']}",
            "Listen to your body's hunger and fullness cues.",
            "Consider consulting a registered dietitian for personalized advice."
        ])
        
        return meal_plan

    except Exception as e:
        print(f"Error in diet recommendation: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return a default balanced plan if there's an error
        return {
            'breakfast': ['Oatmeal with berries and nuts (medium portion)', 'Scrambled eggs with whole wheat toast (medium portion)'],
            'lunch': ['Grilled chicken salad with olive oil dressing (medium portion)', 'Quinoa bowl with roasted vegetables (medium portion)'],
            'dinner': ['Baked salmon with sweet potato (medium portion)', 'Grilled chicken with quinoa (medium portion)'],
            'snacks': [
                'Greek yogurt with mixed berries (small portion)',
                'Handful of almonds (small portion)',
                'Hummus with vegetable sticks (medium portion)'
            ],
            'water_intake': '2.5L',
            'meal_timing': {
                'breakfast': 'Within 1 hour of waking',
                'snack_am': 'Mid-morning',
                'lunch': '4-5 hours after breakfast',
                'snack_pm': 'Mid-afternoon',
                'dinner': 'At least 2-3 hours before bedtime'
            },
            'nutritional_info': {
                'target_calories': 2000,
                'protein_g': 100,
                'carbs_g': 200,
                'fats_g': 67,
                'fiber_g': 30
            },
            'notes': [
                'This is a default meal plan. Please check the logs for errors.',
                'Stay hydrated and adjust portion sizes based on your activity level.',
                'Consult a healthcare professional for personalized dietary advice.'
            ]
        }

# Routes
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Basic validation
        if not username or not email or not password:
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('register'))
        
        # Check if user already exists (case-insensitive for email, case-sensitive for username)
        user = User.query.filter((User.email == email.lower()) | (User.username == username)).first()
        if user:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))
            
        try:
            # Create new user with hashed password
            # Username is saved exactly as provided by the user (no restrictions)
            hashed_password = generate_password_hash(password)
            new_user = User(
                username=username,  # Save username as-is (any name user wants)
                email=email.lower(),  # Normalize email to lowercase
                password=hashed_password
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Registration error: {str(e)}")
            flash('Error creating account. Please try again.', 'danger')
            return redirect(url_for('register'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        try:
            identifier = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if not identifier or not password:
                flash('Please enter both email/username and password', 'danger')
                return redirect(url_for('login'))
            
            # Check if user exists with email or username
            user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()
            
            if user and check_password_hash(user.password, password):
                login_user(user, remember=True)
                next_page = request.args.get('next')
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(next_page or url_for('home'))
            
            flash('Invalid email/username or password', 'danger')
            
        except Exception as e:
            app.logger.error(f'Login error: {str(e)}')
            flash('An error occurred during login. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    latest_assessment = HealthAssessment.query.filter_by(user_id=current_user.id).order_by(HealthAssessment.date.desc()).first()
    
    if request.method == 'POST':
        try:
            # Get form data
            age = int(request.form.get('age'))
            weight = float(request.form.get('weight'))
            height = float(request.form.get('height'))
            gender = request.form.get('gender')
            activity_level = request.form.get('activity_level')
            goal = request.form.get('goal')
            dietary_restrictions = request.form.get('dietary_restrictions', '')
            health_conditions = request.form.get('health_conditions', '')
            
            # Create a new assessment with the updated data
            new_assessment = HealthAssessment(
                user_id=current_user.id,
                age=age,
                weight=weight,
                height=height,
                gender=gender,
                activity_level=activity_level,
                goal=goal,
                target_weight=latest_assessment.target_weight if latest_assessment else weight,
                bmi=0,  # Will be recalculated
                bmi_category='',  # Will be recalculated
                daily_calories=latest_assessment.daily_calories if latest_assessment else 0,
                expected_weeks=latest_assessment.expected_weeks if latest_assessment else 1
            )
            
            # Recalculate BMI
            height_m = height / 100
            bmi = round(weight / (height_m ** 2), 1)
            
            # Determine BMI category
            if bmi < 18.5:
                bmi_category = "Underweight"
            elif 18.5 <= bmi < 25:
                bmi_category = "Normal weight"
            elif 25 <= bmi < 30:
                bmi_category = "Overweight"
            else:
                bmi_category = "Obese"
                
            new_assessment.bmi = bmi
            new_assessment.bmi_category = bmi_category
            
            # Update user's dietary restrictions and health conditions
            current_user.dietary_restrictions = dietary_restrictions
            current_user.health_conditions = health_conditions
            
            # Save to database
            db.session.add(new_assessment)
            db.session.commit()
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('profile.html', assessment=latest_assessment)

@app.route('/upload_profile_picture', methods=['POST'])
@login_required
def upload_profile_picture():
    try:
        if 'profile_picture' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['profile_picture']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            # Create secure filename
            filename = secure_filename(file.filename)
            # Add user ID to make it unique
            unique_filename = f"user_{current_user.id}_{filename}"
            
            # Ensure upload directory exists
            upload_dir = os.path.join(app.static_folder, 'uploads', 'profile_pictures')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            
            # Update user's profile image in database
            current_user.profile_image = f'uploads/profile_pictures/{unique_filename}'
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'image_url': url_for('static', filename=current_user.profile_image)
            })
        
        return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/health-assessment", methods=["GET", "POST"])
@login_required
def health_assessment():
    # Check if user has an active assessment (within last 1 week)
    one_week_ago = datetime.utcnow() - timedelta(weeks=1)
    latest_assessment = HealthAssessment.query.filter(
        HealthAssessment.user_id == current_user.id,
        HealthAssessment.date >= one_week_ago
    ).order_by(HealthAssessment.date.desc()).first()
    
    # If GET request and active assessment exists, load assessment data for editing
    if request.method == "GET" and latest_assessment:
        # Pre-fill form with existing assessment data
        return render_template('health_assessment.html', 
                           age=latest_assessment.age,
                           weight=latest_assessment.weight,
                           height=latest_assessment.height,
                           gender=latest_assessment.gender,
                           activity_level=latest_assessment.activity_level,
                           goal=latest_assessment.goal,
                           target_weight=latest_assessment.target_weight,
                           disease_type=latest_assessment.disease_type,
                           allergies=latest_assessment.allergies,
                           preferred_cuisine=latest_assessment.preferred_cuisine)
        
    if request.method == "POST":
        try:
            # Get form data
            age = int(request.form.get("age"))
            weight = float(request.form.get("weight"))
            height = float(request.form.get("height"))
            gender = request.form.get("gender")
            activity_level = request.form.get("activity_level")
            goal = request.form.get("goal")
            target_weight = float(request.form.get("target_weight", weight))
            disease_type = request.form.get("disease_type", "None")
            allergies = request.form.get("allergies", None)
            preferred_cuisine = request.form.get("preferred_cuisine", None)
            
            # Calculate BMI
            height_m = height / 100
            bmi = round(weight / (height_m ** 2), 1)
            
            # Determine BMI category
            if bmi < 18.5:
                bmi_category = "Underweight"
            elif 18.5 <= bmi < 25:
                bmi_category = "Normal weight"
            elif 25 <= bmi < 30:
                bmi_category = "Overweight"
            else:
                bmi_category = "Obese"
            
            # Calculate daily calorie needs
            if gender.lower() == 'male':
                bmr = 10 * weight + 6.25 * height - 5 * age + 5
            else:  # female
                bmr = 10 * weight + 6.25 * height - 5 * age - 161
                
            activity_multipliers = {
                'sedentary': 1.2,
                'light': 1.375,
                'moderate': 1.55,
                'active': 1.725,
                'very_active': 1.9
            }
            
            goal_adjustment = 1.0
            if goal == 'weight_loss':
                goal_adjustment = 0.85
            elif goal == 'muscle_gain':
                goal_adjustment = 1.15
                
            daily_calories = round(bmr * activity_multipliers.get(activity_level.lower(), 1.2) * goal_adjustment)
            
            # Create assessment
            assessment = HealthAssessment(
                user_id=current_user.id,
                age=age,
                weight=weight,
                height=height,
                gender=gender,
                activity_level=activity_level,
                goal=goal,
                bmi=bmi,
                bmi_category=bmi_category,
                daily_calories=daily_calories,
                target_weight=target_weight,
                expected_weeks=1,  # Default value for 1 week plan
                disease_type=disease_type,
                allergies=allergies,  # Save allergies
                preferred_cuisine=preferred_cuisine  # Save preferred cuisine
            )
            
            db.session.add(assessment)
            db.session.commit()
            
            flash('Health assessment saved successfully!', 'success')
            return redirect(url_for('health_calendar', assessment_id=assessment.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing your assessment: {str(e)}', 'danger')
            return redirect(url_for('health_assessment'))

    return render_template('health_assessment.html')

@app.route("/health-calendar/<int:assessment_id>")
@login_required
def health_calendar(assessment_id):
    assessment = HealthAssessment.query.get_or_404(assessment_id)
    
    # Ensure the assessment belongs to the current user
    if assessment.user_id != current_user.id:
        abort(403)
    
    # Calculate target date (1 week from assessment date)
    target_date = assessment.date + timedelta(weeks=1)
    days_remaining = (target_date.date() - datetime.utcnow().date()).days
    
    # Generate meal plans if they don't exist
    if not assessment.daily_plans:
        # Get personalized meal plan based on user's data
        meal_plan = get_diet_recommendation(
            age=assessment.age,
            weight=assessment.weight,
            height=assessment.height,
            bmi=assessment.bmi,
            disease_type=assessment.disease_type,
            activity_level=assessment.activity_level,
            goal=assessment.goal,
            gender=assessment.gender,
            preferred_cuisine=getattr(assessment, 'preferred_cuisine', None),
            allergies=getattr(assessment, 'allergies', None)
        )
        
        # Create meal plans for 1 week (7 days)
        used_meals = {
            'breakfast': set(),
            'lunch': set(),
            'dinner': set(),
            'snacks': set()
        }
        
        for day in range(7):
            plan_date = assessment.date.date() + timedelta(days=day)
            
            # Get unused meals for variety
            def get_unused_meal(meal_list, meal_type):
                available_meals = [meal for meal in meal_list if meal not in used_meals[meal_type]]
                if available_meals:
                    selected_meal = random.choice(available_meals)
                    used_meals[meal_type].add(selected_meal)
                    return selected_meal
                return random.choice(meal_list) if meal_list else "Default meal"
            
            # Create daily meal plan with variety
            daily_meals = {
                'breakfast': get_unused_meal(meal_plan['breakfast'], 'breakfast'),
                'lunch': get_unused_meal(meal_plan['lunch'], 'lunch'),
                'dinner': get_unused_meal(meal_plan['dinner'], 'dinner'),
                'snack': get_unused_meal(meal_plan['snacks'], 'snacks'),
                'water_intake': meal_plan['water_intake'],
                'notes': meal_plan['notes']
            }
            
            daily_plan = DailyMealPlan(
                assessment_id=assessment.id,
                date=plan_date,
                meals=daily_meals,
                completed=False
            )
            db.session.add(daily_plan)
        
        db.session.commit()
    
    # Get only the first 7 meal plans, ordered by date
    daily_plans = DailyMealPlan.query.filter_by(
        assessment_id=assessment_id
    ).order_by(DailyMealPlan.date).limit(7).all()
    
    # Group plans by week (should only be Week 1)
    weekly_plans = {}
    for plan in daily_plans:
        week_number = (plan.date - assessment.date.date()).days // 7 + 1
        if week_number not in weekly_plans:
            weekly_plans[week_number] = []
        weekly_plans[week_number].append(plan)
    
    return render_template(
        'health_calendar.html',
        assessment=assessment,
        weekly_plans=weekly_plans,
        target_date=target_date.date(),
        days_remaining=days_remaining,
        today=datetime.utcnow().date(),
        progress_percent=round((7 - days_remaining) / 7 * 100) if days_remaining <= 7 else 100
    )

@app.route('/toggle-completion/<int:plan_id>', methods=['POST'])
@login_required
def toggle_completion(plan_id):
    try:
        plan = DailyMealPlan.query.get_or_404(plan_id)
        # Verify the plan belongs to the current user
        assessment = HealthAssessment.query.get(plan.assessment_id)
        if assessment.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        plan.completed = not plan.completed
        db.session.commit()
        return jsonify({'success': True, 'completed': plan.completed})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/today-meals')
@login_required
def api_today_meals():
    """API endpoint to get today's meals for the dashboard"""
    try:
        # Get the latest assessment for the current user
        latest_assessment = HealthAssessment.query.filter_by(user_id=current_user.id).order_by(HealthAssessment.date.desc()).first()
        
        if not latest_assessment:
            return jsonify({'meals': None})
        
        # Get today's meal plan
        today = datetime.utcnow().date()
        today_plan = DailyMealPlan.query.filter_by(
            assessment_id=latest_assessment.id,
            date=today
        ).first()
        
        if today_plan and today_plan.meals:
            return jsonify({'meals': today_plan.meals})
        else:
            return jsonify({'meals': None})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/latest-assessment')
@login_required
def api_latest_assessment():
    """API endpoint to get latest assessment for current user"""
    try:
        latest_assessment = HealthAssessment.query.filter_by(user_id=current_user.id).order_by(HealthAssessment.date.desc()).first()
        
        if not latest_assessment:
            return jsonify({'assessment_id': None})
        
        return jsonify({'assessment_id': latest_assessment.id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health-status')
@login_required
def api_health_status():
    """API endpoint to get health status data for the dashboard"""
    try:
        # Get the latest assessment for the current user
        latest_assessment = HealthAssessment.query.filter_by(user_id=current_user.id).order_by(HealthAssessment.date.desc()).first()
        
        if not latest_assessment:
            return jsonify({
                'meals_completed': 0,
                'total_meals': 7,
                'calories_tracked': 0,
                'target_calories': 2000,
                'streak_days': 0,
                'weekly_progress': 0,
                'health_score': 0,
                'weight': None,
                'calories': 2000,
                'bmi': None
            })
        
        # Get today's meal plan
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())  # Start of current week
        
        # Get all meal plans for the current week
        weekly_plans = DailyMealPlan.query.filter(
            DailyMealPlan.assessment_id == latest_assessment.id,
            DailyMealPlan.date >= week_start,
            DailyMealPlan.date <= today
        ).all()
        
        # Calculate metrics
        total_meals = len(weekly_plans) * 4  # 4 meals per day (breakfast, lunch, dinner, snack)
        completed_meals = sum(1 for plan in weekly_plans if plan.completed) * 4
        
        # Calculate calories (mock calculation - in real app, this would come from meal data)
        target_calories = latest_assessment.daily_calories or 2000
        calories_tracked = min(completed_meals * 500, target_calories)  # Rough estimate
        
        # Calculate streak days
        streak_days = 0
        current_date = today
        while current_date >= week_start:
            day_plan = DailyMealPlan.query.filter_by(
                assessment_id=latest_assessment.id,
                date=current_date
            ).first()
            if day_plan and day_plan.completed:
                streak_days += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        # Calculate weekly progress
        weekly_progress = round((completed_meals / max(total_meals, 1)) * 100) if total_meals > 0 else 0
        
        return jsonify({
            'meals_completed': completed_meals // 4,  # Convert back to days
            'total_meals': len(weekly_plans),
            'calories_tracked': calories_tracked,
            'target_calories': target_calories,
            'streak_days': streak_days,
            'weekly_progress': weekly_progress,
            'health_score': 0,  # Will be calculated on frontend
            'weight': latest_assessment.weight,
            'calories': target_calories,
            'bmi': latest_assessment.bmi
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save-notes/<int:plan_id>', methods=['POST'])
@login_required
def save_notes(plan_id):
    try:
        data = request.get_json()
        plan = DailyMealPlan.query.get_or_404(plan_id)
        
        # Verify the plan belongs to the current user
        assessment = HealthAssessment.query.get(plan.assessment_id)
        if assessment.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        plan.notes = data.get('notes', '')
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download-diet-plan/<int:assessment_id>')
@login_required
def download_diet_plan(assessment_id):
    try:
        # Get assessment and verify ownership
        assessment = HealthAssessment.query.get_or_404(assessment_id)
        if assessment.user_id != current_user.id:
            abort(403)
        
        # Get all meal plans for this assessment
        daily_plans = DailyMealPlan.query.filter_by(
            assessment_id=assessment_id
        ).order_by(DailyMealPlan.date).all()
        
        if not daily_plans:
            flash('No meal plans found for this assessment', 'danger')
            return redirect(url_for('health_calendar', assessment_id=assessment_id))
        
        # Create PDF in memory
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=12,
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#10b981'),
            spaceAfter=10,
            spaceBefore=10
        )
        
        # Build PDF content
        content = []
        
        # Title
        content.append(Paragraph(f"Your {current_user.username}'s One-Week Diet Plan", title_style))
        content.append(Paragraph(f"<b>Generated on:</b> {datetime.utcnow().strftime('%B %d, %Y')}", styles['Normal']))
        content.append(Spacer(1, 0.2*inch))
        
        # User info summary
        content.append(Paragraph("<b>Health Profile Summary:</b>", heading_style))
        
        user_info = [
            ['Health Goal:', assessment.goal.replace('_', ' ').title() if assessment.goal else 'N/A'],
            ['BMI:', f"{assessment.bmi} ({assessment.bmi_category})"],
            ['Daily Calorie Target:', f"{assessment.daily_calories} kcal"],
            ['Activity Level:', assessment.activity_level.replace('_', ' ').title() if assessment.activity_level else 'N/A'],
            ['Health Condition:', assessment.disease_type if assessment.disease_type and assessment.disease_type != 'None' else 'None'],
        ]
        
        user_table = Table(user_info, colWidths=[2.5*inch, 3.5*inch])
        user_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0fdf4')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        content.append(user_table)
        content.append(Spacer(1, 0.3*inch))
        
        # Daily meal plans
        content.append(Paragraph("<b>Daily Meal Plans:</b>", heading_style))
        
        for idx, plan in enumerate(daily_plans, 1):
            content.append(Paragraph(f"<b>Day {idx}: {plan.date.strftime('%A, %B %d, %Y')}</b>", styles['Heading3']))
            
            meals_info = [
                ['Breakfast:', plan.meals.get('breakfast', 'N/A')],
                ['Lunch:', plan.meals.get('lunch', 'N/A')],
                ['Dinner:', plan.meals.get('dinner', 'N/A')],
                ['Snack:', plan.meals.get('snack', 'N/A')],
                ['Water Intake:', plan.meals.get('water_intake', '2.5L')],
            ]
            
            meals_table = Table(meals_info, colWidths=[1.5*inch, 4.5*inch])
            meals_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e0f2fe')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
            ]))
            content.append(meals_table)
            content.append(Spacer(1, 0.15*inch))
        
        # Add notes section
        content.append(PageBreak())
        content.append(Paragraph("<b>Important Notes:</b>", heading_style))
        
        notes = [
            f"<b>Prepared for:</b> {current_user.username}",
            f"<b>Plan Duration:</b> {daily_plans[0].date.strftime('%B %d')} to {daily_plans[-1].date.strftime('%B %d, %Y')}",
            "<b>Nutritional Information:</b>",
            f"• Daily Calorie Target: {assessment.daily_calories} kcal",
            "• Adjust portions based on your hunger and activity levels",
            "• Stay hydrated throughout the day",
            "• Consult with a healthcare professional before making major dietary changes",
            "• Feel free to swap meals with similar nutritional profiles",
        ]
        
        for note in notes:
            content.append(Paragraph(note, styles['Normal']))
            content.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(content)
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"diet_plan_{current_user.username}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        )
    
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('health_calendar', assessment_id=assessment_id))

@app.route('/ai-chat', methods=['GET', 'POST'])
@login_required
def ai_chat():
    if request.method == 'POST':
        user_message = request.form.get('message')
        
        if not user_message:
            return jsonify({'response': "Please provide a message."}), 400
        
        try:
            print(f"[DEBUG] current_user.id: {getattr(current_user, 'id', None)} user_message: {user_message}")
            # Get the user's latest health assessment for profile context (most recent regardless of status)
            user_profile = HealthAssessment.query.filter_by(user_id=current_user.id).order_by(HealthAssessment.date.desc()).first()

            # Resolve the most-relevant daily meal plan: prefer today, then next upcoming, then any plan
            daily_plan = None
            if user_profile:
                today = datetime.utcnow().date()
                try:
                    daily_plan = DailyMealPlan.query.filter_by(assessment_id=user_profile.id, date=today).first()
                except Exception:
                    daily_plan = None

                if not daily_plan:
                    try:
                        # Next upcoming plan (including today)
                        daily_plan = DailyMealPlan.query.filter(
                            DailyMealPlan.assessment_id == user_profile.id,
                            DailyMealPlan.date >= today
                        ).order_by(DailyMealPlan.date).first()
                    except Exception:
                        daily_plan = None

                if not daily_plan:
                    try:
                        # Any plan for the assessment
                        daily_plan = DailyMealPlan.query.filter_by(assessment_id=user_profile.id).order_by(DailyMealPlan.date).first()
                    except Exception:
                        daily_plan = None

            # If there's no stored DailyMealPlan, generate a lightweight recommendation and wrap it
            if not daily_plan and user_profile:
                try:
                    generated = get_diet_recommendation(
                        age=user_profile.age,
                        weight=user_profile.weight,
                        height=user_profile.height,
                        bmi=user_profile.bmi,
                        disease_type=user_profile.disease_type,
                        activity_level=user_profile.activity_level,
                        goal=user_profile.goal,
                        gender=user_profile.gender,
                        preferred_cuisine=getattr(user_profile, 'preferred_cuisine', None),
                        allergies=getattr(user_profile, 'allergies', None)
                    )
                    # Wrap generated plan so chatbot can access `.meals`
                    # Ensure `.meals` is a dict with keys breakfast/lunch/dinner/snacks
                    meals_dict = {
                        'breakfast': generated.get('breakfast', []),
                        'lunch': generated.get('lunch', []),
                        'dinner': generated.get('dinner', []),
                        'snacks': generated.get('snacks', [])
                    }
                    daily_plan = SimpleNamespace(meals=meals_dict)
                except Exception:
                    daily_plan = None

            # Load recent chat history for context (last 10)
            try:
                recent_db_chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.timestamp.desc()).limit(10).all()
                # Reverse to oldest->newest order
                recent_chats = list(reversed(recent_db_chats))
            except Exception:
                recent_chats = []

            # Get AI response from chatbot module (pass profile, diet plan, and recent chats)
            ai_response = ai_chatbot_response(user_message, chats=recent_chats, profile=user_profile, diet_plan=daily_plan)

            # Persist the chat exchange

            try:
                new_chat = Chat(user_id=current_user.id, user_message=user_message, bot_message=ai_response)
                db.session.add(new_chat)
                db.session.commit()
                print(f"[DEBUG] Chat saved: user_id={current_user.id}, user_message={user_message}, bot_message={ai_response}")
                # Print number of chats for this user
                chat_count = Chat.query.filter_by(user_id=current_user.id).count()
                print(f"[DEBUG] Total chats for user {current_user.id}: {chat_count}")
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Failed to save chat: {e}")
                print(f"[DEBUG] Failed to save chat: {e}")

            return jsonify({'response': ai_response})
        except Exception as e:
            print(f"Error in ai_chat route: {str(e)}")
            return jsonify({'response': "I'm sorry, I encountered an error. Please try again later."}), 500
    
    return render_template('ai_chat.html')


@app.route('/chat/history', methods=['GET'])
@login_required
def chat_history():
    try:
        chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.timestamp.asc()).limit(200).all()
        data = []
        for c in chats:
            data.append({
                'id': c.id,
                'user_message': c.user_message,
                'bot_message': c.bot_message,
                'timestamp': c.timestamp.isoformat() if c.timestamp else None
            })
        return jsonify({'history': data})
    except Exception as e:
        app.logger.error(f"Error fetching chat history: {e}")
        return jsonify({'history': []}), 500

def init_db():
    with app.app_context():
        try:
            # Create all database tables
            print("Creating database tables...")
            db.create_all()
            
            # Check if admin user exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                print("Creating admin user...")
                # Create admin user
                hashed_password = generate_password_hash('admin123')
                admin = User(
                    username='admin',
                    email='admin@nutriai.com',
                    password=hashed_password,
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
                print("Username: admin")
                print("Password: admin123")
            else:
                print("Admin user already exists.")
                
            # Verify all required tables exist
            inspector = db.inspect(db.engine)
            required_tables = ['user', 'health_assessment', 'daily_meal_plan']
            for table in required_tables:
                if not inspector.has_table(table):
                    print(f"Warning: Table '{table}' was not created!")
                else:
                    print(f"Table '{table}' exists.")
                    
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            db.session.rollback()
            raise

# DEBUG ROUTE: View all chat records for the current user
if __name__ != '__main__':
    @app.route('/debug/chats')
    @login_required
    def debug_chats():
        chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.timestamp.asc()).all()
        result = []
        for c in chats:
            result.append({
                'id': c.id,
                'user_message': c.user_message,
                'bot_message': c.bot_message,
                'timestamp': c.timestamp.isoformat() if c.timestamp else None
            })
        print(f"[DEBUG] /debug/chats for user {current_user.id}: {result}")
        return jsonify(result)

if __name__ == '__main__':
    # Initialize the database
    init_db()
    # Run the application
    app.run(debug=True)
