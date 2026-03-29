import json

from flask import current_app, session
from sqlalchemy import func

from food_ordering.models import MenuItem, Order, OrderItem
from food_ordering.services.settings import get_ai_settings

try:
    from google import genai
except ImportError:  # pragma: no cover - optional dependency at runtime
    genai = None


def get_personalized_recommendations(limit=3, current_item=None, user=None, anchor_item_ids=None):
    available_items = MenuItem.query.filter_by(is_available=True).order_by(MenuItem.name.asc()).all()
    if not available_items:
        return {"items": [], "source": "none", "reason": None}

    excluded_ids = set(anchor_item_ids or [])
    if current_item:
        excluded_ids.add(current_item.id)

    candidates = [item for item in available_items if item.id not in excluded_ids]
    if not candidates:
        return {"items": [], "source": "none", "reason": None}

    fallback = _fallback_recommendations(
        candidates,
        limit=limit,
        current_item=current_item,
        user=user,
        anchor_item_ids=anchor_item_ids,
    )
    gemini_items = _gemini_recommendations(
        candidates,
        limit=limit,
        current_item=current_item,
        user=user,
        anchor_item_ids=anchor_item_ids,
    )

    if gemini_items:
        reason = _build_reason(user=user, current_item=current_item, ai_used=True, anchor_item_ids=anchor_item_ids)
        return {"items": gemini_items, "source": "gemini", "reason": reason}

    reason = _build_reason(user=user, current_item=current_item, ai_used=False, anchor_item_ids=anchor_item_ids)
    return {"items": fallback, "source": "fallback", "reason": reason}


def _build_reason(user=None, current_item=None, ai_used=False, anchor_item_ids=None):
    if current_item:
        base = f"Based on {current_item.name}, category similarity, and popular combinations"
    elif anchor_item_ids:
        base = "Based on items in your cart, frequently bought together pairs, and popular combinations"
    elif user and getattr(user, "is_authenticated", False):
        base = "Based on your recent orders, cart activity, and popular items"
    else:
        base = "Based on menu popularity and customer ordering patterns"

    if ai_used:
        return f"{base}. Ranked with Gemini."
    return f"{base}. Ranked with local fallback logic."


def _fallback_recommendations(candidates, limit=3, current_item=None, user=None, anchor_item_ids=None):
    history_ids = set(_get_recent_user_item_ids(user))
    cart_ids = set(_get_cart_item_ids())
    anchor_ids = set(anchor_item_ids or [])
    if current_item:
        anchor_ids.add(current_item.id)
    if not anchor_ids:
        anchor_ids = set(cart_ids)

    ranked = []
    for item in candidates:
        score = _popularity_score(item.id)
        score += _co_purchase_score(item.id, anchor_ids)
        if current_item and item.category_id == current_item.category_id:
            score += 8
        if item.id in history_ids:
            score += 5
        if item.id in cart_ids:
            score += 3
        if current_item and current_item.category_id != item.category_id:
            score += 1
        ranked.append((score, item.created_at, item))

    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [row[2] for row in ranked[:limit]]


def _gemini_recommendations(candidates, limit=3, current_item=None, user=None, anchor_item_ids=None):
    ai_settings = get_ai_settings(current_app.config)
    api_key = ai_settings["gemini_api_key"]
    model_name = ai_settings["gemini_model"]
    custom_prompt = ai_settings["recommendation_prompt"]
    if not api_key or genai is None:
        return []

    client = genai.Client(api_key=api_key)
    candidate_payload = [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category.name,
            "description": item.description,
            "price": item.price,
        }
        for item in candidates
    ]

    prompt = (
        f"{custom_prompt}\n"
        "You are ranking menu recommendations for an online food ordering system. "
        "Return strict JSON with this schema: "
        '{"recommended_ids":[int,int,int],"reason":"short text"}. '
        f"Recommend exactly {min(limit, len(candidate_payload))} item ids from this candidate list only. "
        "Use category similarity, order intent, complementary foods, cart context, frequently bought together signals, and purchase history when relevant.\n"
        f"Current item: {json.dumps(_item_context(current_item), ensure_ascii=True)}\n"
        f"User history: {json.dumps(_user_context(user), ensure_ascii=True)}\n"
        f"Cart context: {json.dumps(_cart_context(), ensure_ascii=True)}\n"
        f"Anchor item ids: {json.dumps(list(anchor_item_ids or []), ensure_ascii=True)}\n"
        f"Frequently bought together map: {json.dumps(_pair_context(anchor_item_ids or ([] if not current_item else [current_item.id])), ensure_ascii=True)}\n"
        f"Candidates: {json.dumps(candidate_payload, ensure_ascii=True)}"
    )

    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        payload = json.loads((response.text or "").strip())
    except Exception:
        return []

    recommended_ids = payload.get("recommended_ids", [])
    ordered = []
    lookup = {item.id: item for item in candidates}
    for item_id in recommended_ids:
        item = lookup.get(item_id)
        if item and item not in ordered:
            ordered.append(item)
    return ordered[:limit]


def _item_context(current_item):
    if not current_item:
        return {"active": False}
    return {
        "active": True,
        "id": current_item.id,
        "name": current_item.name,
        "category": current_item.category.name,
        "description": current_item.description,
        "price": current_item.price,
    }


def _user_context(user):
    return {"recent_item_ids": _get_recent_user_item_ids(user)}


def _cart_context():
    item_ids = _get_cart_item_ids()
    items = MenuItem.query.filter(MenuItem.id.in_(item_ids)).all() if item_ids else []
    return {
        "item_ids": item_ids,
        "items": [{"id": item.id, "name": item.name, "category": item.category.name} for item in items],
    }


def _get_recent_user_item_ids(user):
    if not user or not getattr(user, "is_authenticated", False):
        return []

    rows = (
        OrderItem.query.join(Order)
        .with_entities(OrderItem.menu_item_id)
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(8)
        .all()
    )
    return [row.menu_item_id for row in rows]


def _get_cart_item_ids():
    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        return []
    item_ids = []
    for item_id in cart.keys():
        try:
            item_ids.append(int(item_id))
        except (TypeError, ValueError):
            continue
    return item_ids


def _popularity_score(item_id):
    total = (
        OrderItem.query.with_entities(func.sum(OrderItem.quantity))
        .filter(OrderItem.menu_item_id == item_id)
        .scalar()
    )
    return int(total or 0)


def _co_purchase_score(item_id, anchor_ids):
    if not anchor_ids:
        return 0

    score = 0
    for anchor_id in anchor_ids:
        if anchor_id == item_id:
            continue
        score += _pair_count(anchor_id, item_id) * 4
    return score


def _pair_context(anchor_item_ids):
    context = {}
    for anchor_id in anchor_item_ids:
        related = _top_pairs_for_item(anchor_id, limit=4)
        if related:
            context[str(anchor_id)] = related
    return context


def _top_pairs_for_item(item_id, limit=4):
    rows = []
    orders = (
        OrderItem.query.with_entities(OrderItem.order_id)
        .filter(OrderItem.menu_item_id == item_id)
        .all()
    )
    order_ids = [row.order_id for row in orders]
    if not order_ids:
        return rows

    pair_rows = (
        OrderItem.query.join(MenuItem)
        .with_entities(OrderItem.menu_item_id, MenuItem.name, func.sum(OrderItem.quantity))
        .filter(OrderItem.order_id.in_(order_ids), OrderItem.menu_item_id != item_id)
        .group_by(OrderItem.menu_item_id, MenuItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )
    for pair_id, pair_name, qty in pair_rows:
        rows.append({"item_id": pair_id, "name": pair_name, "count": int(qty or 0)})
    return rows


def _pair_count(item_a_id, item_b_id):
    if not item_a_id or not item_b_id or item_a_id == item_b_id:
        return 0

    order_rows = (
        OrderItem.query.with_entities(OrderItem.order_id)
        .filter(OrderItem.menu_item_id == item_a_id)
        .all()
    )
    order_ids = [row.order_id for row in order_rows]
    if not order_ids:
        return 0

    total = (
        OrderItem.query.with_entities(func.count(OrderItem.id))
        .filter(OrderItem.order_id.in_(order_ids), OrderItem.menu_item_id == item_b_id)
        .scalar()
    )
    return int(total or 0)
