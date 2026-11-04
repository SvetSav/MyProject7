import uuid

from django.conf import settings


# ============================================================
# Определение режима: mock или реальный Stripe
# ============================================================
def _use_mock() -> bool:
    """
    Mock-режим включается, если:
      - STRIPE_MOCK=true в settings/env, ИЛИ
      - ключ не задан, ИЛИ
      - ключ не похож на реальный sk_test_51...
    """
    if getattr(settings, "STRIPE_MOCK", False):
        return True

    key = (getattr(settings, "STRIPE_SECRET_KEY", "") or "").strip()

    # реальный ключ Stripe начинается с sk_test_51... (длинный)
    if key.startswith("sk_test_51") and len(key) > 40:
        return False

    # пустой, плейсхолдер или кириллица → mock
    return True


# Реальный stripe импортируем только когда нужен
if not _use_mock():
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY


# ============================================================
# Mock-хранилище (в памяти процесса)
# ============================================================
_mock_products: dict = {}
_mock_prices: dict = {}
_mock_sessions: dict = {}


def _fake_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


# ============================================================
# Сервисные функции (единый интерфейс для mock и real)
# ============================================================
def create_stripe_product(name: str, description: str = "") -> dict:
    """Создаёт продукт (mock или real)."""
    if _use_mock():
        pid = _fake_id("prod")
        _mock_products[pid] = {"name": name, "description": description}
        return {"id": pid, "name": name, "mock": True}

    try:
        product = stripe.Product.create(
            name=name,
            description=description[:500] if description else "",
        )
        return {"id": product.id, "name": product.name, "mock": False}
    except stripe.error.StripeError as e:
        raise Exception(
            f"Ошибка Stripe при создании продукта: {e.user_message or str(e)}"
        )


def create_stripe_price(product_id: str, amount: int, currency: str = "rub") -> dict:
    """
    Создаёт цену. amount — в минимальных единицах (копейки).
    """
    if _use_mock():
        price_id = _fake_id("price")
        _mock_prices[price_id] = {
            "product_id": product_id,
            "amount": amount,
            "currency": currency,
        }
        return {
            "id": price_id,
            "unit_amount": amount,
            "currency": currency,
            "mock": True,
        }

    try:
        price = stripe.Price.create(
            product=product_id,
            unit_amount=amount,
            currency=currency,
        )
        return {
            "id": price.id,
            "unit_amount": price.unit_amount,
            "currency": price.currency,
            "mock": False,
        }
    except stripe.error.StripeError as e:
        raise Exception(f"Ошибка Stripe при создании цены: {e.user_message or str(e)}")


def create_stripe_checkout_session(
    price_id: str,
    success_url: str,
    cancel_url: str,
    metadata: dict | None = None,
) -> dict:
    """Создаёт Checkout Session и возвращает ссылку на оплату."""
    if _use_mock():
        session_id = _fake_id("cs_test")
        price_data = _mock_prices.get(price_id, {"amount": 0, "currency": "rub"})
        _mock_sessions[session_id] = {
            "price_id": price_id,
            "amount": price_data["amount"],
            "currency": price_data["currency"],
            "status": "unpaid",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata or {},
        }
        # mock-ссылка: сразу ведёт на success_url (эмуляция мгновенной оплаты)
        return {
            "session_id": session_id,
            "url": f"{success_url}?mock_session={session_id}",
            "payment_status": "unpaid",
            "mock": True,
        }

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
        )
        return {
            "session_id": session.id,
            "url": session.url,
            "payment_status": session.payment_status,
            "mock": False,
        }
    except stripe.error.StripeError as e:
        raise Exception(
            f"Ошибка Stripe при создании сессии: {e.user_message or str(e)}"
        )


def retrieve_stripe_session(session_id: str) -> dict:
    """Возвращает статус сессии. В mock — эмулирует успешную оплату."""
    if _use_mock():
        if session_id not in _mock_sessions:
            raise Exception(
                f"Mock-сессия {session_id} не найдена. Создайте платёж заново."
            )
        s = _mock_sessions[session_id]
        # при первом запросе статуса — «оплата прошла»
        s["status"] = "paid"
        return {
            "session_id": session_id,
            "payment_status": "paid",
            "amount_total": s["amount"],
            "currency": s["currency"],
            "customer_email": None,
            "mock": True,
        }

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "session_id": session.id,
            "payment_status": session.payment_status,
            "amount_total": session.amount_total,
            "currency": session.currency,
            "customer_email": getattr(session, "customer_email", None),
            "mock": False,
        }
    except stripe.error.StripeError as e:
        raise Exception(
            f"Ошибка Stripe при получении сессии: {e.user_message or str(e)}"
        )
