from food_ordering.models import MenuItem


def _get_cart_storage(session):
    cart = session.get("cart")
    if not isinstance(cart, dict):
        cart = {}
        session["cart"] = cart
    return cart


def add_to_cart(session, item_id, quantity=1):
    cart = _get_cart_storage(session)
    key = str(item_id)
    cart[key] = cart.get(key, 0) + max(quantity, 1)
    session.modified = True


def update_cart_item(session, item_id, quantity):
    cart = _get_cart_storage(session)
    key = str(item_id)
    if quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = quantity
    session.modified = True


def clear_cart(session):
    session["cart"] = {}
    session.modified = True


def get_cart_items(session):
    cart = _get_cart_storage(session)
    item_ids = [int(item_id) for item_id in cart.keys()]
    if not item_ids:
        return []

    items = MenuItem.query.filter(MenuItem.id.in_(item_ids)).all()
    lookup = {item.id: item for item in items}
    rows = []

    for raw_id, quantity in cart.items():
        item = lookup.get(int(raw_id))
        if not item or not item.is_available:
            continue
        subtotal = item.price * quantity
        rows.append(
            {
                "item": item,
                "quantity": quantity,
                "subtotal": subtotal,
            }
        )
    return rows


def get_cart_summary(session):
    items = get_cart_items(session)
    total_quantity = sum(row["quantity"] for row in items)
    total_amount = sum(row["subtotal"] for row in items)
    return {
        "items": items,
        "total_quantity": total_quantity,
        "total_amount": total_amount,
    }
