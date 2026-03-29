from food_ordering import create_app, db
from food_ordering.models import Category, MenuItem, User

app = create_app()

sample_categories = [
    {"name": "Pizza", "description": "Stone-baked pizzas with classic and signature toppings."},
    {"name": "Burgers", "description": "Grilled burgers with fresh toppings and sauces."},
    {"name": "Pasta", "description": "Comfort pasta dishes with rich sauces."},
    {"name": "Desserts", "description": "Sweet endings for every order."},
]

sample_items = [
    {
        "category": "Pizza",
        "name": "Margherita Supreme",
        "description": "Fresh mozzarella, basil, tomato sauce, and olive oil.",
        "price": 32.0,
        "prep_time": 18,
        "image_url": "https://images.unsplash.com/photo-1513104890138-7c749659a591",
    },
    {
        "category": "Pizza",
        "name": "Spicy Chicken Ranch",
        "description": "Roasted chicken, jalapenos, ranch drizzle, and roasted peppers.",
        "price": 39.0,
        "prep_time": 20,
        "image_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836",
    },
    {
        "category": "Burgers",
        "name": "Smoky House Burger",
        "description": "Beef patty, cheddar, caramelized onion, lettuce, and house sauce.",
        "price": 28.0,
        "prep_time": 15,
        "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd",
    },
    {
        "category": "Pasta",
        "name": "Creamy Alfredo Penne",
        "description": "Penne pasta in parmesan cream sauce with grilled chicken.",
        "price": 31.0,
        "prep_time": 17,
        "image_url": "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9",
    },
    {
        "category": "Desserts",
        "name": "Molten Chocolate Cake",
        "description": "Warm chocolate cake served with vanilla cream.",
        "price": 18.0,
        "prep_time": 10,
        "image_url": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c",
    },
]

with app.app_context():
    db.create_all()

    for category_data in sample_categories:
        category = Category.query.filter_by(name=category_data["name"]).first()
        if not category:
            category = Category(**category_data)
            db.session.add(category)

    db.session.flush()

    categories = {category.name: category for category in Category.query.all()}
    for item_data in sample_items:
        existing = MenuItem.query.filter_by(name=item_data["name"]).first()
        if existing:
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
        admin = User(name="Admin User", email="admin@foodsystem.local", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    demo_user = User.query.filter_by(email="customer@foodsystem.local").first()
    if not demo_user:
        demo_user = User(name="Demo Customer", email="customer@foodsystem.local", role="customer")
        demo_user.set_password("customer123")
        db.session.add(demo_user)

    db.session.commit()
    print("Seed completed. Demo admin: admin@foodsystem.local / admin123")
    print("Demo customer: customer@foodsystem.local / customer123")
