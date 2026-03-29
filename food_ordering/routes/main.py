from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from food_ordering import db
from food_ordering.models import Category, MenuItem, Order, OrderItem
from food_ordering.services.cart import add_to_cart, clear_cart, get_cart_summary, update_cart_item
from food_ordering.services.recommendations import get_personalized_recommendations
from food_ordering.services.reports import get_dashboard_metrics, get_status_breakdown, get_top_selling_items
from food_ordering.services.settings import get_ai_settings, set_setting

main_bp = Blueprint("main", __name__)

ORDER_STATUSES = ("pending", "preparing", "out for delivery", "delivered", "cancelled")
PAYMENT_METHODS = ("Card", "Cash on Delivery", "Wallet")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if not current_user.is_admin:
            flash("Admin access is required for this page.", "danger")
            return redirect(url_for("main.index"))
        return view(*args, **kwargs)

    return wrapped


@main_bp.context_processor
def inject_cart_summary():
    return {"cart_summary": get_cart_summary(session)}


@main_bp.route("/")
def index():
    featured_items = MenuItem.query.filter_by(is_available=True).order_by(MenuItem.created_at.desc()).limit(6).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    user_orders = []
    ai_recommendations = get_personalized_recommendations(limit=3, user=current_user)

    if current_user.is_authenticated:
        user_orders = (
            Order.query.filter_by(user_id=current_user.id)
            .order_by(Order.created_at.desc())
            .limit(3)
            .all()
        )

    return render_template(
        "index.html",
        featured_items=featured_items,
        categories=categories,
        user_orders=user_orders,
        ai_recommendations=ai_recommendations,
    )


@main_bp.route("/menu")
def menu():
    search = request.args.get("search", "").strip()
    category_name = request.args.get("category", "").strip()

    query = MenuItem.query.join(Category)
    if search:
        query = query.filter(
            or_(
                MenuItem.name.ilike(f"%{search}%"),
                MenuItem.description.ilike(f"%{search}%"),
            )
        )
    if category_name:
        query = query.filter(Category.name == category_name)

    items = query.order_by(Category.name.asc(), MenuItem.name.asc()).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template(
        "menu.html",
        items=items,
        categories=categories,
        selected_category=category_name,
        search=search,
    )


@main_bp.route("/menu/<int:item_id>")
def menu_item_detail(item_id):
    item = MenuItem.query.get_or_404(item_id)
    ai_recommendations = get_personalized_recommendations(limit=3, current_item=item, user=current_user)
    return render_template("item_detail.html", item=item, ai_recommendations=ai_recommendations)


@main_bp.route("/cart/add/<int:item_id>", methods=["POST"])
def cart_add(item_id):
    item = MenuItem.query.get_or_404(item_id)
    quantity = request.form.get("quantity", "1").strip()
    try:
        quantity_value = max(int(quantity), 1)
    except ValueError:
        quantity_value = 1

    if not item.is_available:
        flash("This item is currently unavailable.", "warning")
        return redirect(request.referrer or url_for("main.menu"))

    add_to_cart(session, item.id, quantity_value)
    flash(f"{item.name} added to cart.", "success")
    return redirect(request.referrer or url_for("main.cart"))


@main_bp.route("/cart", methods=["GET", "POST"])
def cart():
    if request.method == "POST":
        for key, value in request.form.items():
            if not key.startswith("qty_"):
                continue
            item_id = key.replace("qty_", "", 1)
            try:
                update_cart_item(session, int(item_id), int(value))
            except ValueError:
                continue
        flash("Cart updated.", "info")
        return redirect(url_for("main.cart"))

    cart_summary = get_cart_summary(session)
    anchor_item_ids = [row["item"].id for row in cart_summary["items"]]
    ai_recommendations = get_personalized_recommendations(
        limit=3,
        user=current_user,
        anchor_item_ids=anchor_item_ids,
    )
    return render_template("cart.html", cart=cart_summary, ai_recommendations=ai_recommendations)


@main_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = get_cart_summary(session)
    if not cart["items"]:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("main.menu"))

    if request.method == "POST":
        address = request.form.get("delivery_address", "").strip()
        payment_method = request.form.get("payment_method", "").strip()
        note = request.form.get("customer_note", "").strip()

        if not address or payment_method not in PAYMENT_METHODS:
            flash("Delivery address and payment method are required.", "danger")
            return render_template("checkout.html", cart=cart, payment_methods=PAYMENT_METHODS)

        order = Order(
            user_id=current_user.id,
            payment_method=payment_method,
            payment_status="paid" if payment_method != "Cash on Delivery" else "pending",
            delivery_address=address,
            customer_note=note or None,
            total_amount=cart["total_amount"],
        )
        db.session.add(order)
        db.session.flush()

        for row in cart["items"]:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    menu_item_id=row["item"].id,
                    quantity=row["quantity"],
                    unit_price=row["item"].price,
                    line_total=row["subtotal"],
                )
            )

        db.session.commit()
        clear_cart(session)
        flash("Order placed successfully.", "success")
        return redirect(url_for("main.order_detail", order_id=order.id))

    return render_template("checkout.html", cart=cart, payment_methods=PAYMENT_METHODS)


@main_bp.route("/orders")
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("my_orders.html", orders=orders)


@main_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if not current_user.is_admin and order.user_id != current_user.id:
        flash("You are not allowed to view this order.", "danger")
        return redirect(url_for("main.index"))
    return render_template("order_detail.html", order=order)


@main_bp.route("/admin")
@admin_required
def admin_dashboard():
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    return render_template(
        "admin_dashboard.html",
        metrics=get_dashboard_metrics(),
        status_data=get_status_breakdown(),
        top_items=get_top_selling_items(),
        recent_orders=recent_orders,
    )


@main_bp.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    if request.method == "POST":
        gemini_api_key = request.form.get("gemini_api_key", "").strip()
        gemini_model = request.form.get("gemini_model", "").strip() or "gemini-2.5-flash"
        recommendation_prompt = request.form.get("recommendation_prompt", "").strip()

        set_setting("gemini_api_key", gemini_api_key)
        set_setting("gemini_model", gemini_model)
        set_setting("recommendation_prompt", recommendation_prompt)
        db.session.commit()

        flash("AI settings updated.", "success")
        return redirect(url_for("main.admin_settings"))

    settings = get_ai_settings(current_app.config)
    masked_key = ""
    if settings["gemini_api_key"]:
        masked_key = f"{settings['gemini_api_key'][:4]}{'*' * max(len(settings['gemini_api_key']) - 8, 4)}{settings['gemini_api_key'][-4:]}"
    return render_template("admin_settings.html", settings=settings, masked_key=masked_key)


@main_bp.route("/admin/menu", methods=["GET", "POST"])
@admin_required
def admin_menu():
    categories = Category.query.order_by(Category.name.asc()).all()

    if request.method == "POST":
        category_id = request.form.get("category_id", "").strip()
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "").strip()
        prep_time = request.form.get("prep_time", "").strip()
        image_url = request.form.get("image_url", "").strip()

        try:
            price_value = float(price)
            prep_time_value = int(prep_time or 20)
        except ValueError:
            flash("Price and preparation time must be valid numbers.", "danger")
            return redirect(url_for("main.admin_menu"))

        item = MenuItem(
            category_id=int(category_id),
            name=name,
            description=description,
            price=price_value,
            prep_time=prep_time_value,
            image_url=image_url or None,
            is_available=True,
        )
        db.session.add(item)
        db.session.commit()
        flash("Menu item created.", "success")
        return redirect(url_for("main.admin_menu"))

    items = MenuItem.query.join(Category).order_by(Category.name.asc(), MenuItem.name.asc()).all()
    return render_template("admin_menu.html", categories=categories, items=items)


@main_bp.route("/admin/menu/<int:item_id>/toggle", methods=["POST"])
@admin_required
def toggle_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    item.is_available = not item.is_available
    db.session.commit()
    flash("Menu item availability updated.", "info")
    return redirect(url_for("main.admin_menu"))


@main_bp.route("/admin/orders", methods=["GET", "POST"])
@admin_required
def admin_orders():
    if request.method == "POST":
        order_id = request.form.get("order_id", "").strip()
        status = request.form.get("status", "").strip()
        if status in ORDER_STATUSES:
            order = Order.query.get_or_404(int(order_id))
            order.status = status
            db.session.commit()
            flash("Order status updated.", "success")
        return redirect(url_for("main.admin_orders"))

    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin_orders.html", orders=orders, statuses=ORDER_STATUSES)
