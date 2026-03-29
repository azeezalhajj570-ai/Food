# Smart Online Food Ordering and Restaurant Management System

Smart Online Food Ordering and Restaurant Management System is a Flask-based graduation project for digital restaurant operations. It combines customer registration, menu browsing, search, shopping cart, checkout, order tracking, and an administrative dashboard for menu management and sales reporting.

## Current Capabilities

- User registration, login, and logout with session-based authentication.
- Menu browsing with category filtering and search.
- Product detail pages and session-backed shopping cart.
- Checkout flow with delivery address, payment method selection, and order creation.
- Customer order history and order detail tracking.
- Admin dashboard with revenue, order metrics, status summaries, and top-selling items.
- Admin menu management and order status updates.
- JSON API endpoints for health checks, menu listing, cart summary, and order reports.

## Tech Stack

- Flask
- Flask-SQLAlchemy
- Flask-Login
- SQLite
- Tailwind CSS via CDN

## Project Structure

```text
app.py
config.py
seed_data.py
requirements.txt
food_ordering/
  routes/        # Web and API routes
  services/      # Cart and reporting helpers
  templates/     # Jinja templates and UI components
  static/        # Shared styling assets
  models.py      # SQLAlchemy models
```

## Setup

1. Create and activate a virtual environment.
2. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Seed sample data:

```bash
python seed_data.py
```

4. Run the application:

```bash
python app.py
```

5. Open the app in your browser:

```text
http://127.0.0.1:5000
```

## Main Web Routes

- `/` homepage with featured menu items and quick access sections
- `/menu` searchable food catalog
- `/menu/<id>` menu item details
- `/cart` shopping cart
- `/checkout` order placement
- `/orders` current user order history
- `/orders/<id>` order detail
- `/admin` admin dashboard
- `/admin/menu` menu management
- `/admin/orders` order workflow management
- `/login`, `/register`, `/logout` authentication routes

## API Routes

### `GET /api/health`

Returns a small service health payload.

### `GET /api/menu?category=Pizza`

Returns available menu items, optionally filtered by category.

### `GET /api/cart`

Returns the current session cart summary.

### `GET /api/reports/orders`

Returns order totals and status breakdown data.

## Notes

- The database is created automatically on first run.
- Seed data creates sample categories, menu items, an admin account, and a demo customer account.
- Online payment is modeled as an academic-safe mock flow without external gateway integration.
