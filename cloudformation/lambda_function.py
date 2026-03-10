"""
Lambda handler for Retail Shopping API.
Routes: search_products, get_product_details, get_cart, add_to_cart, remove_from_cart, checkout
"""
import boto3
import json
import os
import uuid
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
product_table = dynamodb.Table(os.environ["PRODUCT_TABLE"])
customer_table = dynamodb.Table(os.environ["CUSTOMER_TABLE"])
cart_table = dynamodb.Table(os.environ["CART_TABLE"])
order_table = dynamodb.Table(os.environ["ORDER_TABLE"])


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def respond(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def search_products(params):
    """Search products by category, brand, gender, price range, or keyword."""
    category = params.get("category")
    brand = params.get("brand")
    query = params.get("query", "").lower()
    gender = params.get("gender", "").lower()
    min_price = float(params.get("min_price", 0))
    max_price = float(params.get("max_price", 99999))
    size = params.get("size", "").upper()

    # Use GSI if filtering by category or brand, otherwise scan
    if category:
        resp = product_table.query(
            IndexName="category-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("category").eq(category),
        )
    elif brand:
        resp = product_table.query(
            IndexName="brand-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("brand").eq(brand),
        )
    else:
        resp = product_table.scan()

    items = resp.get("Items", [])

    # Apply filters
    results = []
    for item in items:
        price = float(item.get("price", 0))
        if price < min_price or price > max_price:
            continue
        if gender and item.get("gender", "").lower() not in (gender, "unisex"):
            continue
        if size and size not in item.get("sizes", {}):
            continue
        if query:
            searchable = f"{item.get('name', '')} {item.get('description', '')} {item.get('brand', '')}".lower()
            if query not in searchable:
                continue
        results.append({
            "product_id": item["product_id"],
            "name": item["name"],
            "brand": item["brand"],
            "category": item["category"],
            "price": item["price"],
            "colors": item.get("colors", []),
            "available_sizes": [s for s, qty in item.get("sizes", {}).items() if int(qty) > 0],
            "rating": item.get("rating"),
        })

    return respond(200, {"products": results, "count": len(results)})


def get_product_details(params):
    """Get full details for a single product."""
    product_id = params.get("product_id")
    if not product_id:
        return respond(400, {"error": "product_id is required"})

    resp = product_table.get_item(Key={"product_id": product_id})
    item = resp.get("Item")
    if not item:
        return respond(404, {"error": "Product not found"})

    return respond(200, item)


def get_cart(params):
    """Get all items in a customer's cart."""
    customer_id = params.get("customer_id")
    if not customer_id:
        return respond(400, {"error": "customer_id is required"})

    resp = cart_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("customer_id").eq(customer_id)
    )
    items = resp.get("Items", [])
    subtotal = sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in items)

    return respond(200, {
        "customer_id": customer_id,
        "items": items,
        "item_count": len(items),
        "subtotal": round(subtotal, 2),
    })


def add_to_cart(body):
    """Add a product to the cart."""
    customer_id = body.get("customer_id")
    product_id = body.get("product_id")
    size = body.get("size", "").upper()
    quantity = int(body.get("quantity", 1))

    if not all([customer_id, product_id, size]):
        return respond(400, {"error": "customer_id, product_id, and size are required"})

    # Verify product exists and size is in stock
    resp = product_table.get_item(Key={"product_id": product_id})
    product = resp.get("Item")
    if not product:
        return respond(404, {"error": "Product not found"})

    stock = int(product.get("sizes", {}).get(size, 0))
    if stock < quantity:
        return respond(400, {
            "error": f"Insufficient stock. Only {stock} available in size {size}",
            "available_sizes": [s for s, q in product.get("sizes", {}).items() if int(q) > 0],
        })

    cart_item_id = f"CI-{uuid.uuid4().hex[:8].upper()}"
    cart_table.put_item(Item={
        "customer_id": customer_id,
        "cart_item_id": cart_item_id,
        "product_id": product_id,
        "product_name": product["name"],
        "brand": product["brand"],
        "size": size,
        "quantity": quantity,
        "price": product["price"],
        "added_at": datetime.utcnow().isoformat(),
    })

    return respond(200, {
        "message": f"Added {product['name']} (Size {size}) to cart",
        "cart_item_id": cart_item_id,
    })


def remove_from_cart(body):
    """Remove an item from the cart."""
    customer_id = body.get("customer_id")
    cart_item_id = body.get("cart_item_id")

    if not all([customer_id, cart_item_id]):
        return respond(400, {"error": "customer_id and cart_item_id are required"})

    cart_table.delete_item(Key={"customer_id": customer_id, "cart_item_id": cart_item_id})
    return respond(200, {"message": "Item removed from cart"})


def checkout(body):
    """Process checkout: validate cart, create order, clear cart."""
    customer_id = body.get("customer_id")
    payment_method = body.get("payment_method")

    if not all([customer_id, payment_method]):
        return respond(400, {"error": "customer_id and payment_method are required"})

    # Get cart items
    resp = cart_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("customer_id").eq(customer_id)
    )
    cart_items = resp.get("Items", [])

    if not cart_items:
        return respond(400, {"error": "Cart is empty"})

    # Calculate totals
    subtotal = sum(float(i["price"]) * int(i.get("quantity", 1)) for i in cart_items)
    tax = round(subtotal * 0.08, 2)  # 8% tax
    total = round(subtotal + tax, 2)

    # Create order
    order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"
    order_table.put_item(Item={
        "order_id": order_id,
        "customer_id": customer_id,
        "items": [{
            "product_name": i["product_name"],
            "brand": i["brand"],
            "size": i["size"],
            "quantity": int(i.get("quantity", 1)),
            "price": i["price"],
        } for i in cart_items],
        "subtotal": Decimal(str(subtotal)),
        "tax": Decimal(str(tax)),
        "total": Decimal(str(total)),
        "payment_method": payment_method,
        "status": "confirmed",
        "created_at": datetime.utcnow().isoformat(),
    })

    # Clear cart
    with cart_table.batch_writer() as batch:
        for item in cart_items:
            batch.delete_item(Key={
                "customer_id": customer_id,
                "cart_item_id": item["cart_item_id"],
            })

    return respond(200, {
        "order_id": order_id,
        "status": "confirmed",
        "item_count": len(cart_items),
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "payment_method": payment_method,
        "message": "Order placed successfully!",
    })


def lambda_handler(event, context):
    """Route requests based on path."""
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    params = event.get("queryStringParameters") or {}
    body = {}

    if method == "POST" and event.get("body"):
        body = json.loads(event["body"])

    routes = {
        ("/search_products", "GET"): lambda: search_products(params),
        ("/get_product_details", "GET"): lambda: get_product_details(params),
        ("/get_cart", "GET"): lambda: get_cart(params),
        ("/add_to_cart", "POST"): lambda: add_to_cart(body),
        ("/remove_from_cart", "POST"): lambda: remove_from_cart(body),
        ("/checkout", "POST"): lambda: checkout(body),
    }

    handler = routes.get((path, method))
    if handler:
        return handler()

    return respond(404, {"error": f"Route not found: {method} {path}"})
