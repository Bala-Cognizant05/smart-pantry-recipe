import os
from google.cloud import firestore

# Hardcode the GCP Project ID as required
PROJECT_ID = "qwiklabs-gcp-02-13bb0a69e190"


def seed_database():
    print(f"Initializing Firestore client for project: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)

    recipes = [
        {
            "id": "rec_001",
            "name": "Avocado Chickpea Salad",
            "cuisine": "Mediterranean",
            "cook_time_mins": 15,
            "dietary_tags": ["vegan", "gluten-free"],
            "servings": 2,
            "ingredients": [
                "1 can chickpeas",
                "1 ripe avocado",
                "1 tbsp olive oil",
                "1 tbsp lemon juice",
                "salt and pepper",
            ],
            "instructions": [
                "Rinse and drain chickpeas.",
                "Dice avocado.",
                "Combine chickpeas and avocado in a bowl.",
                "Drizzle with olive oil and lemon juice, season with salt and pepper.",
            ],
        },
        {
            "id": "rec_002",
            "name": "Creamy Mushroom Pasta",
            "cuisine": "Italian",
            "cook_time_mins": 25,
            "dietary_tags": ["vegetarian"],
            "servings": 3,
            "ingredients": [
                "250g fettuccine pasta",
                "200g cremini mushrooms",
                "2 cloves garlic minced",
                "1/2 cup heavy cream",
                "1/4 cup grated parmesan",
            ],
            "instructions": [
                "Boil pasta according to package instructions.",
                "Sauté sliced mushrooms and garlic in butter.",
                "Stir in heavy cream and parmesan.",
                "Toss pasta with sauce and serve warm.",
            ],
        },
        {
            "id": "rec_003",
            "name": "Tofu & Vegetable Stir-Fry",
            "cuisine": "Asian",
            "cook_time_mins": 20,
            "dietary_tags": ["vegan", "gluten-free"],
            "servings": 2,
            "ingredients": [
                "200g firm tofu diced",
                "1 red bell pepper sliced",
                "1 cup broccoli florets",
                "2 tbsp tamari soy sauce",
                "1 tbsp sesame oil",
            ],
            "instructions": [
                "Pan-fry tofu cubes until golden.",
                "Sauté bell pepper and broccoli.",
                "Combine tofu, veggies, and tamari soy sauce.",
                "Serve over steamed rice.",
            ],
        },
    ]

    pantry_items = [
        {
            "id": "pantry_001",
            "item_name": "Chickpeas",
            "quantity": 2.0,
            "unit": "cans",
            "category": "Canned Goods",
        },
        {
            "id": "pantry_002",
            "item_name": "Avocado",
            "quantity": 3.0,
            "unit": "pieces",
            "category": "Produce",
        },
        {
            "id": "pantry_003",
            "item_name": "Olive Oil",
            "quantity": 1.0,
            "unit": "bottle",
            "category": "Pantry Staples",
        },
        {
            "id": "pantry_004",
            "item_name": "Fettuccine Pasta",
            "quantity": 500.0,
            "unit": "grams",
            "category": "Dry Goods",
        },
    ]

    print("Seeding 'recipes' collection...")
    for rec in recipes:
        doc_ref = db.collection("recipes").document(rec["id"])
        doc_ref.set(rec)
        print(f"  - Added recipe: {rec['name']} ({rec['id']})")

    print("Seeding 'pantry_items' collection...")
    for item in pantry_items:
        doc_ref = db.collection("pantry_items").document(item["id"])
        doc_ref.set(item)
        print(f"  - Added pantry item: {item['item_name']} ({item['id']})")

    print("Seeding complete!")


if __name__ == "__main__":
    seed_database()
