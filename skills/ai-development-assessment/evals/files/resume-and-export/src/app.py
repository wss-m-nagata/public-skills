def create_order(payload):
    return {"id": 1, **payload}


def get_order(order_id):
    return {"id": order_id}
