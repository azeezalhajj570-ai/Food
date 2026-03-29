from flask import Blueprint, jsonify, request, session
from flask_login import current_user

from food_ordering.models import MenuItem, Order
from food_ordering.services.recommendations import get_personalized_recommendations
from food_ordering.services.cart import get_cart_summary
from food_ordering.services.reports import get_status_breakdown

api_bp = Blueprint("api", __name__)


@api_bp.route("/health")
def health():
    return jsonify({"status": "ok", "service": "food-ordering-system"})


@api_bp.route("/menu")
def menu():
    category = request.args.get("category", "").strip()
    query = MenuItem.query.filter_by(is_available=True)
    if category:
        query = query.join(MenuItem.category).filter_by(name=category)
    items = query.order_by(MenuItem.name.asc()).all()
    return jsonify(
        [
            {
                "id": item.id,
                "name": item.name,
                "price": item.price,
                "prep_time": item.prep_time,
                "category": item.category.name,
            }
            for item in items
        ]
    )


@api_bp.route("/cart")
def cart():
    summary = get_cart_summary(session)
    return jsonify(
        {
            "total_quantity": summary["total_quantity"],
            "total_amount": summary["total_amount"],
            "items": [
                {
                    "id": row["item"].id,
                    "name": row["item"].name,
                    "quantity": row["quantity"],
                    "subtotal": row["subtotal"],
                }
                for row in summary["items"]
            ],
        }
    )


@api_bp.route("/reports/orders")
def order_report():
    return jsonify(
        {
            "total_orders": Order.query.count(),
            "statuses": get_status_breakdown(),
        }
    )


@api_bp.route("/recommendations")
def recommendations():
    item_id = request.args.get("item_id", type=int)
    use_cart = request.args.get("use_cart", "").strip().lower() in {"1", "true", "yes"}
    current_item = MenuItem.query.get(item_id) if item_id else None
    cart_item_ids = []
    if use_cart:
        raw_cart = session.get("cart", {})
        if isinstance(raw_cart, dict):
            for key in raw_cart.keys():
                try:
                    cart_item_ids.append(int(key))
                except (TypeError, ValueError):
                    continue
    data = get_personalized_recommendations(
        limit=3,
        current_item=current_item,
        user=current_user,
        anchor_item_ids=cart_item_ids,
    )
    return jsonify(
        {
            "source": data["source"],
            "reason": data["reason"],
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category.name,
                    "price": item.price,
                }
                for item in data["items"]
            ],
        }
    )
