import os
import time
import re
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
try:
    load_dotenv()
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    # Set default values if .env file fails to load
    os.environ.setdefault('GROQ_API_KEY', 'your_groq_api_key_here')

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Health and nutrition related keywords
HEALTH_NUTRITION_KEYWORDS = {
    'nutrition': ['nutrition', 'nutrient', 'nutrients', 'nutritious', 'eating', 'diet', 'dietary'],
    'health': ['health', 'healthy', 'disease', 'illness', 'medical', 'wellness', 'wellbeing'],
    'diet': ['diet', 'dieting', 'calorie', 'calories', 'weight loss', 'weight gain', 'meal plan', 
             'meal prep', 'meals', 'food', 'foods', 'eating plan', 'recipes', 'cooking'],
    'fitness': ['fitness', 'exercise', 'workout', 'training', 'gym', 'stretching', 'yoga', 
                'running', 'walking', 'strength', 'cardio', 'physical activity'],
    'conditions': ['diabetes', 'hypertension', 'cholesterol', 'obesity', 'allergies', 'allergy',
                   'intolerance', 'celiac', 'lactose', 'heart disease', 'blood pressure', 
                   'protein', 'vitamin', 'mineral', 'supplement', 'supplements'],
    'lifestyle': ['sleep', 'stress', 'hydration', 'water intake', 'lifestyle', 'habit', 'habits']
}

# Default system message
DEFAULT_SYSTEM_MESSAGE = """
You are NutriAI, a friendly and knowledgeable AI nutritionist. Your goal is to provide 
helpful, accurate, and practical nutrition advice. Be supportive, professional, and 
encourage healthy eating habits. If you don't know something, be honest about it.

When responding to greetings (like "hi", "hello", "thank you", etc.), respond warmly and 
briefly, then offer to help with health/nutrition topics.

IMPORTANT FORMATTING RULES:
- When creating diet plans, use markdown tables for better readability
- Format tables with columns like: Day/Meal | Food Item | Calories | Protein
- Use bullet points for lists of foods or meal options
- Use bold (**text**) for important information like calorie counts or meal names
- Use markdown format for any structured data or tables
- Always make responses clear and well-organized

IMPORTANT: Only answer questions related to nutrition, health, diet, fitness, and wellness.
Do not answer questions about unrelated topics (like politics, sports, technology, general knowledge, etc.).
Just respond that you can only help with health and nutrition topics.
"""

def is_health_related_question(user_message):
    """
    Check if the user's message is related to health, nutrition, diet, or fitness.
    Also allows general greetings and polite phrases.
    
    Args:
        user_message (str): The user's message
        
    Returns:
        bool: True if message is health-related or a greeting, False otherwise
    """
    message_lower = user_message.lower().strip()
    
    # Allow general greetings and polite phrases
    greetings_and_polite = [
        'hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 
        'good evening', 'good night', 'howdy', 'sup',
        'thank you', 'thanks', 'thank u', 'thx', 'appreciate it', 'much appreciated',
        'please', 'ok', 'okay', 'alright', 'sure', 'yes', 'no',
        'how are you', 'how are you doing', 'how do you do', 'what\'s up', "what's up",
        'how can you help', 'what can you do', 'who are you', 'what are you',
        'help', 'assist me', 'can you help', 'good bye', 'goodbye', 'bye', 'see you',
        'catch you later', 'take care', 'have a good day'
    ]
    
    # Check if message is a greeting or polite phrase
    for phrase in greetings_and_polite:
        if message_lower == phrase or message_lower.startswith(phrase + ' ') or message_lower.endswith(' ' + phrase):
            return True
    
    # Check for health/nutrition keywords
    for category, keywords in HEALTH_NUTRITION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                return True
    
    # Check for common health-related patterns
    health_patterns = [
        r'\b(should i eat|can i eat|what should i eat|best food|best diet)\b',
        r'\b(calories|macros|nutrients|vitamins|minerals)\b',
        r'\b(how many|how much|recommended|daily intake)\b',
        r'\b(health goal|fitness goal|weight|bmi)\b',
        r'\b(pain|ache|discomfort|symptom)\b',
        r'\b(tired|fatigue|energy|strength)\b',
        # Add cooking and recipe patterns
        r'\b(how to (make|prepare|cook)|recipe|instructions|steps)\b',
        r'\b(prepare|cook|make|bake|grill|roast|steam|fry|sauté|boil)\b',
        r'\b(food|meal|dish|cuisine|ingredients)\b',
        r'\b(nutrition|healthy|diet|eating)\b.*\b(recipe|cook|prepare)\b',
        r'\b(can you show me|can you tell me)\b.*\b(how|what)\b.*\b(cook|make|prepare)\b'
    ]
    
    for pattern in health_patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False


# Map common unhealthy items to healthier alternatives
UNHEALTHY_SUBSTITUTIONS = {
    'fried chicken': 'grilled or baked chicken; choose a side salad instead of fries',
    'pizza': 'try a thin-crust veggie pizza or a salad with lean protein',
    'soda': 'sparkling water with lemon or infused water',
    'ice cream': 'frozen yogurt or a banana "nice-cream"',
    'chips': 'air-popped popcorn or vegetable sticks with hummus',
    'burger': 'lean turkey or plant-based burger with a whole-grain bun and extra veggies',
    'fries': 'baked sweet potato fries or roasted vegetables',
    'donut': 'whole-grain toast with nut butter and fruit',
    'processed meat': 'grilled fish, legumes, or a lean poultry option',
    'sugary cereal': 'oatmeal topped with fresh fruit and nuts'
}


def detect_unhealthy_items(text):
    """Return a list of unhealthy items found in text (case-insensitive)."""
    found = []
    if not text:
        return found
    lower = text.lower()
    for item in UNHEALTHY_SUBSTITUTIONS.keys():
        # simple substring match is fine for common items
        if item in lower:
            found.append(item)
    return found


# Simple recipe hints for common meals (detailed steps suitable for full-day meal prep)
RECIPE_HINTS = {
    'baked salmon': [
        'Preheat oven to 200°C (400°F).',
        'Pat salmon fillets dry with paper towels.',
        'Season both sides with salt, pepper, olive oil, and fresh lemon slices.',
        'Place on a baking sheet lined with parchment paper.',
        'Bake for 12–15 minutes until the salmon is opaque and flakes easily with a fork.',
        'Serve with steamed vegetables (broccoli, asparagus) or a fresh garden salad.',
        'Drizzle with extra virgin olive oil and squeeze of fresh lemon juice.'
    ],
    'grilled chicken': [
        'Place chicken breast between plastic wrap and pound to 1/2 inch thickness.',
        'Marinate in olive oil, lemon juice, minced garlic, salt, pepper, and herbs for 15–30 minutes.',
        'Preheat grill or grill pan to medium-high heat.',
        'Brush grill grates with oil to prevent sticking.',
        'Grill chicken 5–7 minutes per side until internal temperature reaches 75°C (165°F).',
        'Transfer to a warm plate and let rest for 5 minutes before slicing.',
        'Serve with grilled vegetables or a side salad.'
    ],
    'oatmeal with berries and nuts': [
        'Combine 1/2 cup rolled oats with 1 cup milk (dairy or plant-based) and a pinch of salt in a pot.',
        'Bring to a simmer over medium heat.',
        'Stir occasionally and cook for 5–7 minutes until the oatmeal reaches your desired consistency.',
        'Top with 1/2 cup fresh berries (blueberries, strawberries, raspberries).',
        'Add 1 tablespoon of chopped almonds or walnuts.',
        'Drizzle with honey or maple syrup if desired.',
        'Add a dash of cinnamon for extra flavor.'
    ],
    'quinoa bowl with vegetables': [
        'Rinse 1 cup uncooked quinoa thoroughly under cold water.',
        'Combine quinoa with 2 cups water or vegetable broth in a pot.',
        'Bring to a boil, then reduce heat and simmer for 12–15 minutes until water is absorbed.',
        'While quinoa cooks, chop vegetables: bell peppers, cucumbers, carrots, tomatoes, red onion.',
        'Sauté harder vegetables (carrots, peppers) in 1 tablespoon olive oil until tender.',
        'Fluff cooked quinoa with a fork and transfer to a bowl.',
        'Add sautéed and fresh vegetables, chickpeas or tofu for protein.',
        'Dress with lemon juice, olive oil, salt, pepper, and fresh herbs.'
    ],
    'scrambled eggs with spinach': [
        'Whisk 2–3 eggs in a bowl with a splash of milk, salt, and black pepper.',
        'Heat a non-stick pan over medium heat and add 1 tablespoon butter or olive oil.',
        'Add 1 cup fresh spinach and sauté until wilted, about 1–2 minutes.',
        'Pour the whisked eggs into the pan with the spinach.',
        'Gently stir with a spatula, pushing cooked portions toward the center.',
        'Cook until eggs are creamy and set, about 2–3 minutes.',
        'Transfer to a plate and serve with whole-grain toast and fresh fruit.'
    ],
    'smoothie bowl with granola': [
        'Add 1 cup frozen mixed berries to a blender.',
        'Add 1 banana (fresh or frozen), 1/2 cup Greek yogurt, and 1/2 cup milk.',
        'Add 1 tablespoon almond butter and 1 teaspoon honey.',
        'Blend on high until thick and creamy (not too liquid).',
        'Pour into a bowl.',
        'Top with 1/4 cup granola, sliced fresh fruit, coconut flakes, and chia seeds.',
        'Serve immediately with a spoon.'
    ],
    'grilled chicken salad': [
        'Follow the grilled chicken recipe above and slice the cooked chicken into strips.',
        'Wash and dry mixed salad greens (romaine, spinach, arugula).',
        'Chop fresh vegetables: tomatoes, cucumbers, bell peppers, red onion.',
        'Toss greens and vegetables together in a large bowl.',
        'Add sliced grilled chicken on top.',
        'Dress with extra virgin olive oil, lemon juice, salt, and pepper.',
        'Optional: add feta cheese, nuts, or avocado for extra flavor and nutrition.'
    ],
    'vegetable stir-fry': [
        'Prep all vegetables: slice broccoli, carrots, bell peppers, snap peas, and onions into bite-sized pieces.',
        'If using protein, slice chicken, tofu, or shrimp into small, even pieces.',
        'Heat a wok or large skillet over high heat and add 2 tablespoons oil.',
        'Add protein first (if using) and cook until nearly done; remove and set aside.',
        'Add harder vegetables (carrots, broccoli) and stir-fry for 2–3 minutes.',
        'Add softer vegetables (peppers, snap peas) and stir-fry for another 2 minutes.',
        'Return protein to the wok, add sauce (soy sauce, ginger, garlic), and toss for 1 minute.',
        'Serve over steamed rice or noodles.'
    ],
    'baked sweet potato fries': [
        'Preheat oven to 220°C (425°F).',
        'Wash and pat dry 2–3 medium sweet potatoes.',
        'Cut into fries about 1/4 inch thick and 3–4 inches long.',
        'Toss fries in a bowl with 2 tablespoons olive oil, salt, pepper, and optional spices (paprika, garlic powder, cumin).',
        'Spread in a single layer on a parchment-lined baking sheet.',
        'Bake for 20–30 minutes, stirring halfway through, until golden and crispy.',
        'Serve hot with a side of plain Greek yogurt or a light dipping sauce.'
    ],
    'miso soup with rice': [
        'Rinse 1/2 cup Japanese short-grain rice and cook with 1 cup water (1:1 ratio) until fluffy.',
        'In a pot, combine 2 cups water with 1 tablespoon dried kombu (kelp) and heat.',
        'Just before boiling, remove kombu and add 1 tablespoon dried bonito flakes (katsuobushi).',
        'Simmer for 5–7 minutes to infuse flavor, then strain.',
        'In a small bowl, dissolve 2 tablespoons miso paste with 3 tablespoons warm broth.',
        'Pour the miso mixture into the hot broth and stir gently (do not boil).',
        'Add soft tofu cubes and wakame seaweed if desired.',
        'Serve miso soup in bowls with cooked rice on the side.'
    ],
    'tempura': [
        'Prepare batter: whisk 1/2 cup flour, 1/2 cup cornstarch, 1/2 teaspoon baking powder, and 1/2 cup ice-cold soda water in a bowl.',
        'Cut vegetables (zucchini, sweet potato, carrots, bell peppers) and seafood (shrimp, scallops) into bite-sized pieces.',
        'Lightly coat vegetables and seafood in flour, shaking off excess.',
        'Fill a deep pan with 2–3 inches of vegetable oil and heat to 165°C (350°F).',
        'Dip floured items into tempura batter until fully coated.',
        'Carefully place in hot oil and fry until golden brown, about 2–3 minutes.',
        'Remove with a slotted spoon and drain on paper towels.',
        'Serve with steamed rice, a small bowl of dipping sauce, and fresh ginger.'
    ],
    'sukiyaki': [
        'Slice 200g beef thinly (partially freeze for easier slicing).',
        'Prep vegetables: slice napa cabbage, cut carrots into strips, slice shiitake mushrooms, cut tofu into cubes.',
        'Make sukiyaki sauce: combine 1/2 cup dashi, 1/4 cup soy sauce, 2 tablespoons sugar, and 1 tablespoon mirin.',
        'Heat a shallow sukiyaki pan or large skillet over medium-high heat.',
        'Add a small piece of beef fat or oil to coat the pan.',
        'Arrange beef and vegetables in the pan.',
        'Pour sauce over ingredients and cook 5–7 minutes until vegetables are tender and beef is cooked.',
        'Eat by dipping cooked items in raw beaten eggs (optional traditional style) or serve with sauce.'
    ],
    'salad': [
        'Wash and dry mixed salad greens (romaine, spinach, arugula, or iceberg lettuce).',
        'Chop fresh vegetables: tomatoes, cucumbers, bell peppers, carrots, red onion.',
        'Add protein: grilled chicken, canned tuna, boiled eggs, beans, or tofu.',
        'Toss greens and vegetables together in a large salad bowl.',
        'In a small bowl, whisk together 3 tablespoons extra virgin olive oil, 1 tablespoon balsamic or white vinegar, salt, pepper, and optional Dijon mustard.',
        'Drizzle dressing over salad and toss until well coated.',
        'Top with nuts, seeds, or cheese if desired.',
        'Serve immediately.'
    ],
    'pad thai': [
        'Soak 200g rice noodles in warm water for 15–20 minutes until softened; drain.',
        'Prep vegetables: slice bell peppers, cut carrots into thin strips, slice green onions.',
        'Make pad thai sauce: combine 3 tablespoons tamarind paste, 3 tablespoons fish sauce, 2 tablespoons palm sugar, and 1 tablespoon lime juice.',
        'Heat 2 tablespoons oil in a wok over high heat.',
        'Add minced garlic and cook for 30 seconds until fragrant.',
        'Add protein (shrimp, chicken, or tofu) and cook until nearly done.',
        'Add drained noodles and sauce; toss for 2–3 minutes.',
        'Add vegetables and toss for another minute.',
        'Serve with crushed peanuts, fresh lime wedges, and cilantro on top.'
    ],
    'butter chicken': [
        'Marinate 500g chicken (cut into chunks) in yogurt, ginger, garlic, and spices for 30 minutes.',
        'Heat 2 tablespoons ghee or oil in a large pan and sear chicken until golden; set aside.',
        'In the same pan, sauté onions until golden.',
        'Add ginger-garlic paste and cook for 1 minute.',
        'Add tomato puree and cook for 2–3 minutes.',
        'Stir in garam masala, turmeric, chili powder, and salt.',
        'Return chicken to the pan and add 1/2 cup cream and 1 tablespoon butter.',
        'Simmer for 10–12 minutes until chicken is cooked and sauce is creamy.',
        'Serve with steamed basmati rice or naan bread.'
    ]
}



def get_prep_instructions_for_meal(meal_name):
    """Return detailed prep steps for a meal name if available, else a generic prep template."""
    if not meal_name:
        return None
    key = meal_name.lower()
    
    # Try to find a matching hint by substring match
    for k in RECIPE_HINTS.keys():
        if k in key:
            return RECIPE_HINTS[k]
    
    # Enhanced generic preparation instructions based on food type
    def get_generic_prep(food_name):
        food_lower = food_name.lower()
        
        # Vegetables
        if any(veg in food_lower for veg in ['broccoli', 'carrot', 'spinach', 'tomato', 'potato', 'onion', 'garlic', 'bell pepper', 'cucumber', 'lettuce', 'cauliflower', 'zucchini', 'mushroom']):
            return [
                f'Wash {food_name} thoroughly under running water.',
                'Remove any damaged parts or peels as needed.',
                'Cut into desired size (dice, slice, or chop).',
                'Choose cooking method: steam, roast, sauté, or eat raw.',
                'Season with herbs, salt, pepper, and a touch of olive oil.',
                'Cook until tender-crisp (about 5-10 minutes depending on method).'
            ]
        
        # Proteins
        elif any(protein in food_lower for protein in ['chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna', 'shrimp', 'tofu', 'eggs']):
            return [
                f'Pat {food_name} dry with paper towels.',
                'Season with salt, pepper, and your favorite herbs/spices.',
                'Choose cooking method: grill, bake, pan-sear, or poach.',
                f'Cook {food_name} until internal temperature is safe (165°F/74°C for chicken, 145°F/63°C for beef/pork).',
                'Let rest for 3-5 minutes before serving.',
                'Serve with lemon wedges or fresh herbs.'
            ]
        
        # Grains/Carbs
        elif any(grain in food_lower for grain in ['rice', 'pasta', 'quinoa', 'oats', 'bread', 'couscous', 'barley']):
            return [
                f'Measure appropriate portion of {food_name} (typically 1/2-1 cup cooked).',
                'Rinse grains (except pasta) under cold water.',
                'Cook according to package directions.',
                'For rice: use 2:1 water-to-rice ratio, simmer 15-20 minutes.',
                'For pasta: boil in salted water until al dente.',
                'Fluff with fork and season to taste.'
            ]
        
        # Fruits
        elif any(fruit in food_lower for fruit in ['apple', 'banana', 'orange', 'berry', 'strawberry', 'blueberry', 'grape', 'melon', 'pineapple', 'mango']):
            return [
                f'Wash {food_name} thoroughly.',
                'Remove peels, seeds, or cores as needed.',
                'Cut into bite-sized pieces or slices.',
                'Serve fresh or add to salads/yogurt.',
                'For enhanced flavor: add a squeeze of lemon or a sprinkle of cinnamon.',
                'Best served at room temperature for optimal flavor.'
            ]
        
        # Legumes/Beans
        elif any(legume in food_lower for legume in ['beans', 'lentils', 'chickpeas', 'peas']):
            return [
                f'Rinse {food_name} thoroughly if using canned.',
                'If using dried: soak overnight, then cook until tender.',
                'Season with herbs like cumin, coriander, or paprika.',
                'Add to soups, salads, or serve as a side dish.',
                'Cook for 20-30 minutes until tender.',
                'Drain excess liquid and season to taste.'
            ]
        
        # Dairy
        elif any(dairy in food_lower for dairy in ['yogurt', 'cheese', 'milk', 'cottage cheese']):
            return [
                f'Serve {food_name} chilled or at room temperature.',
                'Portion control: 1/2 cup yogurt, 1-2 oz cheese, 1 cup milk.',
                'Add fresh fruits, nuts, or herbs for flavor.',
                'Use in cooking or as a topping.',
                'Check expiration date before use.',
                'Store properly in refrigerator.'
            ]
        
        # Nuts/Seeds
        elif any(nut in food_lower for nut in ['almond', 'walnut', 'cashew', 'peanut', 'seed', 'chia', 'flax']):
            return [
                f'Use unsalted, raw {food_name} for maximum health benefits.',
                'Portion: small handful (1/4 cup) per serving.',
                'Toast lightly in dry pan for enhanced flavor (2-3 minutes).',
                'Add to salads, yogurt, or eat as snack.',
                'Store in airtight container to maintain freshness.',
                'Great source of healthy fats and protein.'
            ]
        
        # Default generic instructions
        else:
            return [
                f'Check {food_name} for freshness and quality.',
                'Follow package cooking instructions if available.',
                'Use appropriate cooking method for the food type.',
                'Season minimally to preserve natural flavors.',
                'Control portion sizes for balanced nutrition.',
                'Serve with complementary foods for complete meal.'
            ]
    
    return get_generic_prep(meal_name)


def find_meals_in_text(meal_list, text):
    """Return meals from meal_list that are mentioned in text (case-insensitive substring match)."""
    found = []
    if not meal_list or not text:
        return found
    lower = text.lower()
    for meal in meal_list:
        if meal and meal.lower() in lower:
            found.append(meal)
    return found

def get_system_message(profile, diet_plan=None):
    """Generate a system message based on user profile and optional diet plan

    Args:
        profile: HealthAssessment-like object (may be None)
        diet_plan: DailyMealPlan-like object (may be None)
    """
    if not profile and not diet_plan:
        return DEFAULT_SYSTEM_MESSAGE

    profile_info = []
    if profile:
        if hasattr(profile, 'goal') and profile.goal:
            profile_info.append(f"The user's main health goal is: {profile.goal}")
        if hasattr(profile, 'disease_type') and profile.disease_type:
            profile_info.append(f"The user has mentioned the following health condition: {profile.disease_type}")
        if hasattr(profile, 'age') and profile.age:
            profile_info.append(f"The user's age is: {profile.age}")
        if hasattr(profile, 'weight') and profile.weight:
            profile_info.append(f"The user's weight is: {profile.weight} kg")

    # Add diet plan summary if provided
    diet_info = []
    if diet_plan and hasattr(diet_plan, 'meals') and diet_plan.meals:
        try:
            meals = diet_plan.meals
            # meals expected to be a dict with keys like 'breakfast','lunch','dinner','snack'
            diet_info.append("Today's meal plan:")
            for k in ['breakfast', 'lunch', 'dinner', 'snack', 'snacks']:
                if k in meals and meals[k]:
                    diet_info.append(f"{k.capitalize()}: {meals[k]}")
        except Exception:
            pass

    parts = [DEFAULT_SYSTEM_MESSAGE]
    if profile_info:
        parts.append("Here's what I know about the user:\n- " + "\n- ".join(profile_info))
    if diet_info:
        parts.append("\n".join(diet_info))

    return "\n\n".join(parts)

def ai_chatbot_response(user_message, chats, profile=None, diet_plan=None):
    """
    Generate a response from the AI nutritionist using Groq API
    
    Args:
        user_message (str): The user's message
        chats (list): List of previous chat messages
        profile (User): User profile object (optional)
        
    Returns:
        str: The AI's response
    """
    try:
        # Check if the question is health/nutrition related
        if not is_health_related_question(user_message):
            return """I appreciate your question, but I'm specifically designed to help with health, 
nutrition, diet, and fitness topics. I can't assist with other subjects. 

Could you ask me something about:
- Nutrition and meal planning
- Diet and weight management
- Fitness and exercise
- Health conditions and wellness
- Vitamins, minerals, and supplements

I'm here to help you achieve your health goals! 🥗"""
        
        # Check if API key is available
        if not os.getenv("GROQ_API_KEY"):
            return """I'm currently unable to connect to the AI service. 
            Please ensure the GROQ_API_KEY is set in your environment variables."""
        
        # Prepare the messages list with system message (include profile and diet plan)
        messages = [{"role": "system", "content": get_system_message(profile, diet_plan)}]

        # Detect if user mentions having eaten unhealthy items and inject quick substitution hints
        try:
            unhealthy = detect_unhealthy_items(user_message)
            if unhealthy:
                subs = []
                for it in unhealthy:
                    alt = UNHEALTHY_SUBSTITUTIONS.get(it)
                    if alt:
                        subs.append(f"{it} -> {alt}")

                if subs:
                    substitution_note = (
                        "The user mentioned they ate some less-healthy items. "
                        "When responding, provide brief, non-judgmental swap suggestions and a short recovery tip. "
                        "Examples of swaps: " + "; ".join(subs) + ". "
                        "Also suggest one short recovery tip (e.g., hydrate, balance next meal)."
                    )
                    messages.append({"role": "system", "content": substitution_note})
        except Exception:
            pass
        
        # Add previous chat history if available
        if chats:
            for c in chats[-10:]:  # Limit to last 10 exchanges to avoid token limit
                messages.append({"role": "user", "content": c.user_message})
                messages.append({"role": "assistant", "content": c.bot_message})
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})
        
        # Call the Groq API with error handling and retries
        # Detect if user is asking for full-day prep to allocate more tokens
        full_day_request = bool(re.search(r'\b(full day|whole day|all day|entire day|day plan|full day meals)\b', user_message.lower()))
        max_tokens = 2000 if full_day_request else 1000  # Increase for full-day requests
        
        for attempt in range(3):  # Retry up to 3 times
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens
                )
                ai_text = response.choices[0].message.content.strip()

                # Detect if user asked about how to prepare/cook or mentioned meals from their diet plan
                # append concise prep instructions generated locally for reliability.
                try:
                    cooking_query = False
                    # Enhanced cooking query detection
                    cooking_patterns = [
                        r'\b(how to (make|prepare|cook)|recipe|steps|how do i (make|prepare|cook))\b',
                        r'\b(prepare|cook|make|bake|grill|roast|steam|fry|sauté|boil)\b',
                        r'\b(instructions|directions|method|technique)\b',
                        r'\b(how.*can.*i|how.*do.*i|how.*should.*i)\b.*\b(prepare|cook|make)\b',
                        r'\b(what.*to.*do|what.*should.*i.*do)\b.*\b(with|for)\b',
                        r'\b(can.*you.*show.*me|can.*you.*tell.*me)\b.*\b(how|what)\b'
                    ]
                    
                    for pattern in cooking_patterns:
                        if re.search(pattern, user_message.lower()):
                            cooking_query = True
                            break

                    # Detect if user asked for full-day prep (e.g., "full day", "all day", "whole day")
                    full_day_query = False
                    if re.search(r'\b(full day|whole day|all day|entire day|day plan|full day meals)\b', user_message.lower()):
                        full_day_query = True

                    prep_texts = []
                    # Check if diet_plan includes meals to provide prep steps
                    if diet_plan and hasattr(diet_plan, 'meals') and isinstance(diet_plan.meals, dict):
                        meals = diet_plan.meals
                        # If user asked generally about preparing items in the plan, referenced specific ones,
                        # or explicitly asked for a full-day meal prep
                        if full_day_query or cooking_query or any(m.lower() in user_message.lower() for m in [str(x).lower() for x in meals.values() if isinstance(x, str)]):
                            # collect unique meal names
                            meal_names = set()
                            for v in meals.values():
                                if isinstance(v, str):
                                    # If meals are stored as lists, skip those handled below
                                    meal_names.add(v)
                                elif isinstance(v, list):
                                    for it in v:
                                        meal_names.add(it)

                            # For each meal, get prep instructions
                            for meal in meal_names:
                                instr = get_prep_instructions_for_meal(meal)
                                if instr:
                                    prep_texts.append((meal, instr))

                    # If user explicitly mentioned a specific meal not in diet_plan, try to extract meal name from message
                    if (cooking_query or full_day_query) and not prep_texts:
                        # naive extraction: look for quoted phrases (handle double and single quotes separately)
                        double_q = re.findall(r'"([^\"]+)"', user_message)
                        single_q = re.findall(r"'([^']+)'", user_message)
                        flat = double_q + single_q
                        for q in flat:
                            instr = get_prep_instructions_for_meal(q)
                            if instr:
                                prep_texts.append((q, instr))

                    # NEW: Auto-detect food items in any message and provide prep instructions
                    if not prep_texts and cooking_query:
                        # Common food items to detect
                        food_keywords = [
                            'chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna', 'shrimp', 'tofu', 'eggs',
                            'broccoli', 'carrot', 'spinach', 'tomato', 'potato', 'onion', 'garlic', 'bell pepper',
                            'rice', 'pasta', 'quinoa', 'oats', 'bread', 'salad', 'soup', 'stew',
                            'apple', 'banana', 'orange', 'berry', 'strawberry', 'blueberry', 'grape',
                            'yogurt', 'cheese', 'milk', 'beans', 'lentils', 'nuts', 'almond', 'walnut'
                        ]
                        
                        # Find food items mentioned in the message
                        mentioned_foods = []
                        message_lower = user_message.lower()
                        for food in food_keywords:
                            if food in message_lower:
                                mentioned_foods.append(food)
                        
                        # Get prep instructions for detected foods
                        for food in mentioned_foods:
                            instr = get_prep_instructions_for_meal(food)
                            if instr:
                                prep_texts.append((food, instr))

                    if (cooking_query or full_day_query) and prep_texts:
                        appended = '\n\nPreparation steps for requested items:\n'
                        if full_day_query:
                            appended = '\n\nPreparation steps for full-day meal plan:\n'
                        for meal, steps in prep_texts:
                            appended += f"\n{meal}:\n"
                            for i, s in enumerate(steps, start=1):
                                appended += f"{i}. {s}\n"
                        ai_text = ai_text + appended

                except Exception:
                    pass

                return ai_text
                
            except Exception as e:
                if attempt == 2:  # Last attempt
                    raise
                time.sleep(1 * (attempt + 1))  # Simple backoff
                
    except Exception as e:
        # Log the error for debugging
        import traceback
        print(f"Error in ai_chatbot_response: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Full traceback: {traceback.format_exc()}")
        
        # User-friendly error message
        return f"""I apologize, but I'm currently experiencing technical difficulties. 
        Error: {str(e)}
        Please try again in a few moments. If the problem persists, please check your 
        internet connection or contact support if the issue continues."""
    
    # Fallback response
    return "I'm sorry, I couldn't process your request at the moment. Please try again later."

