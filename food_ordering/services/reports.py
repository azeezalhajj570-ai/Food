from sqlalchemy import func

from food_ordering.models import MenuItem, Order, OrderItem


def get_dashboard_metrics():
    total_orders = Order.query.count()
    total_revenue = db_safe_float(db_session_scalar(func.sum(Order.total_amount)))
    pending_orders = Order.query.filter_by(status="pending").count()
    available_items = MenuItem.query.filter_by(is_available=True).count()
    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "pending_orders": pending_orders,
        "available_items": available_items,
    }


def get_status_breakdown():
    rows = (
        Order.query.with_entities(Order.status, func.count(Order.id))
        .group_by(Order.status)
        .order_by(Order.status.asc())
        .all()
    )
    return [{"label": status.title(), "value": count} for status, count in rows]


def get_top_selling_items(limit=5):
    rows = (
        OrderItem.query.join(MenuItem)
        .with_entities(
            MenuItem.name,
            func.sum(OrderItem.quantity).label("sold_qty"),
            func.sum(OrderItem.line_total).label("sales_total"),
        )
        .group_by(MenuItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "name": name,
            "sold_qty": int(sold_qty or 0),
            "sales_total": float(sales_total or 0.0),
        }
        for name, sold_qty, sales_total in rows
    ]


def db_session_scalar(expression):
    from food_ordering import db

    return db.session.query(expression).scalar()


def db_safe_float(value):
    return float(value or 0.0)
