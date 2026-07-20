from engine.types import StandardOrder


def orders_to_wms_items(orders: list) -> list:
    items = []
    for order in orders:
        qty = order.quantity
        try:
            qty = int(qty)
        except (ValueError, TypeError):
            qty = 0
        items.append({
            "order_no": order.order_no or "",
            "receiver_org": order.receiver_org or "",
            "receiver_name": order.receiver_name or "",
            "receiver_phone": order.receiver_phone or "",
            "receiver_address": order.receiver_address or "",
            "item_code": order.item_code or "",
            "item_name": order.item_name or "",
            "quantity": qty,
        })
    return items
