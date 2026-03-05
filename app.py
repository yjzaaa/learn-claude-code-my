
from agents import s05_skill_loading

def main():
    # Load the skill
    skill = s05_skill_loading.load_skill("finance")
    
    # Example user query
    user_query = "What was the total revenue for Q1 2024?"
    
    # Use the skill to generate and execute SQL query
    result = skill.execute(user_query)
    
    print("Query Result:", result)