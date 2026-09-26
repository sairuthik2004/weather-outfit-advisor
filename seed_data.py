import datetime
from google.cloud import firestore

# IMPORTANT: Hardcode project ID as a string literal.
PROJECT_ID = "qwiklabs-gcp-02-25232f8c8134"

def seed_database():
    print(f"Connecting to Firestore for project '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("user_outfit_preferences")

    sample_data = [
        {
            "user_id": "user_101",
            "city": "Seattle",
            "cold_threshold_f": 55,
            "preferred_style": "Casual / Layers",
            "favorite_gear": ["Waterproof Hooded Jacket", "Waterproof Boots", "Wool Beanie"],
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "user_id": "user_102",
            "city": "Miami",
            "cold_threshold_f": 68,
            "preferred_style": "Athletic & Lightweight",
            "favorite_gear": ["Polarized Sunglasses", "Linen Shirts", "Breathable Sneakers"],
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "user_id": "user_103",
            "city": "New York",
            "cold_threshold_f": 50,
            "preferred_style": "Smart / Urban Trench",
            "favorite_gear": ["Wool Trench Coat", "Leather Gloves", "Compact Umbrella"],
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    for item in sample_data:
        doc_ref = collection_ref.document(item["user_id"])
        doc_ref.set(item)
        print(f"Seeded document for {item['user_id']} ({item['city']})")

    print("Firestore database successfully seeded!")

if __name__ == "__main__":
    seed_database()
