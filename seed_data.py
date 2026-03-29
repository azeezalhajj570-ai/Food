from food_ordering import create_app, db
from food_ordering.models import Category, MenuItem, OrderItem, User

sample_categories = [
    {"name": "Fast Food", "description": "Popular quick meals for everyday ordering."},
    {"name": "Drinks", "description": "Fresh juices, iced drinks, and soft beverages."},
    {"name": "Desserts", "description": "Light sweets and classic finishing options."},
    {"name": "Healthy Meals", "description": "Balanced bowls, salads, and grilled choices."},
]

legacy_categories = ["Pizza", "Burgers", "Pasta"]
legacy_items = [
    "Margherita Supreme",
    "Spicy Chicken Ranch",
    "Smoky House Burger",
    "Creamy Alfredo Penne",
    "Molten Chocolate Cake",
]

sample_items = [
    {
        "category": "Fast Food",
        "name": "Classic Chicken Burger",
        "description": "Grilled chicken fillet, lettuce, tomato, and signature sauce.",
        "price": 24.0,
        "prep_time": 14,
        "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd",
    },
    {
        "category": "Fast Food",
        "name": "Loaded Fries Box",
        "description": "Crispy fries topped with cheese sauce, herbs, and chicken bites.",
        "price": 19.0,
        "prep_time": 12,
        "image_url": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877",
    },
    {
        "category": "Drinks",
        "name": "Fresh Orange Juice",
        "description": "Cold fresh orange juice served without artificial additives.",
        "price": 11.0,
        "prep_time": 5,
        "image_url": "https://images.unsplash.com/photo-1600271886742-f049cd451bba",
    },
    {
        "category": "Healthy Meals",
        "name": "Grilled Chicken Bowl",
        "description": "Rice, grilled chicken, roasted vegetables, and lemon herb dressing.",
        "price": 29.0,
        "prep_time": 16,
        "image_url": "https://images.unsplash.com/photo-1547592180-85f173990554",
    },
    {
        "category": "Desserts",
        "name": "Mini Pancake Stack",
        "description": "Soft mini pancakes served with honey and chocolate drizzle.",
        "price": 17.0,
        "prep_time": 10,
        "image_url": "https://images.unsplash.com/photo-1528207776546-365bb710ee93",
    },
    {
        "category": "Drinks",
        "name": "Iced Caramel Latte",
        "description": "Chilled espresso drink with milk and caramel flavor.",
        "price": 14.0,
        "prep_time": 6,
        "image_url": "https://images.unsplash.com/photo-1461023058943-07fcbe16d735",
    },
]

def seed_database():
    app = create_app()

    with app.app_context():
        db.create_all()

        legacy_menu_items = MenuItem.query.filter(MenuItem.name.in_(legacy_items)).all()
        legacy_item_ids = [item.id for item in legacy_menu_items]
        protected_item_ids = {
            row.menu_item_id for row in OrderItem.query.filter(OrderItem.menu_item_id.in_(legacy_item_ids)).all()
        } if legacy_item_ids else set()

        for item in legacy_menu_items:
            if item.id not in protected_item_ids:
                db.session.delete(item)

        db.session.flush()

        for category in Category.query.filter(Category.name.in_(legacy_categories)).all():
            if not category.items:
                db.session.delete(category)

        existing_item_names = {item.name for item in MenuItem.query.all()}

        for category_data in sample_categories:
            category = Category.query.filter_by(name=category_data["name"]).first()
            if not category:
                category = Category(**category_data)
                db.session.add(category)
            else:
                category.description = category_data["description"]

        db.session.flush()

        categories = {category.name: category for category in Category.query.all()}
        for item_data in sample_items:
            if item_data["name"] in existing_item_names:
                continue
            db.session.add(
                MenuItem(
                    category_id=categories[item_data["category"]].id,
                    name=item_data["name"],
                    description=item_data["description"],
                    price=item_data["price"],
                    prep_time=item_data["prep_time"],
                    image_url=item_data["image_url"],
                    is_available=True,
                )
            )

        admin = User.query.filter_by(email="admin@foodsystem.local").first()
        if not admin:
            admin = User(name="Admin User", username="admin", email="admin@foodsystem.local", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
        else:
            admin.username = "admin"

        demo_user = User.query.filter(
            (User.email == "user@example.com") | (User.username == "user")
        ).first()
        if not demo_user:
            demo_user = User(name="Demo User", username="user", email="user@example.com", role="customer")
            db.session.add(demo_user)
        else:
            demo_user.name = "Demo User"
            demo_user.username = "user"
            demo_user.email = "user@example.com"
            demo_user.role = "customer"
        demo_user.set_password("user")

        db.session.commit()
        print("Seed completed. Demo admin: admin@foodsystem.local / admin123")
        print("Demo customer: user@example.com or user / user")


if __name__ == "__main__":
    seed_database()
