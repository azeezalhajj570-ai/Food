from flask import Blueprint, jsonify, request, session

from food_ordering.models import MenuItem, Order
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
