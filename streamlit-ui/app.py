"""
Multi-Brand Clothing Store with AI Shopping Assistant
"""
import streamlit as st
import json
import os
import sys
import base64
import boto3
from io import BytesIO
from decimal import Decimal
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

REGION = os.getenv("aws_default_region", "us-east-1")
PROFILE = os.getenv("awscred_profile_name")

# Product images - using Unsplash for realistic product photos
PRODUCT_IMAGES = {
    # Outerwear
    "PROD-001": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=400&h=500&fit=crop",
    "PROD-008": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=400&h=500&fit=crop",
    # Dresses
    "PROD-002": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=400&h=500&fit=crop",
    "PROD-018": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=500&fit=crop",
    "PROD-019": "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=400&h=500&fit=crop",
    "PROD-020": "https://images.unsplash.com/photo-1583846783214-7229a91b20ed?w=400&h=500&fit=crop",
    "PROD-021": "https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=400&h=500&fit=crop",
    "PROD-022": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=400&h=500&fit=crop",
    # Bottoms
    "PROD-003": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=400&h=500&fit=crop",
    "PROD-006": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=400&h=500&fit=crop",
    "PROD-009": "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=400&h=500&fit=crop",
    "PROD-015": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=400&h=500&fit=crop",
    "PROD-016": "https://images.unsplash.com/photo-1552902865-b72c031ac5ea?w=400&h=500&fit=crop",
    "PROD-017": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=400&h=500&fit=crop",
    # Tops
    "PROD-004": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=500&fit=crop",
    "PROD-007": "https://images.unsplash.com/photo-1576871337632-b9aef4c17ab9?w=400&h=500&fit=crop",
    "PROD-011": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=500&fit=crop",
    "PROD-012": "https://images.unsplash.com/photo-1562157873-818bc0726f68?w=400&h=500&fit=crop",
    "PROD-013": "https://images.unsplash.com/photo-1625910513413-5fc421e0fd4f?w=400&h=500&fit=crop",
    "PROD-014": "https://images.unsplash.com/photo-1598554747436-c9293d6a588f?w=400&h=500&fit=crop",
    # Footwear
    "PROD-010": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=400&h=500&fit=crop",
    "PROD-023": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop",
    "PROD-024": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=500&fit=crop",
    "PROD-025": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=400&h=500&fit=crop",
    "PROD-026": "https://images.unsplash.com/photo-1603487742131-4160ec999306?w=400&h=500&fit=crop",
    # Accessories
    "PROD-005": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400&h=500&fit=crop",
    "PROD-027": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=500&fit=crop",
    "PROD-028": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=500&fit=crop",
    "PROD-029": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400&h=500&fit=crop",
    "PROD-030": "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=500&fit=crop",
    "PROD-031": "https://images.unsplash.com/photo-1588850561407-ed78c334e67a?w=400&h=500&fit=crop",
}

CATEGORY_BANNERS = {
    "all": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1200&h=300&fit=crop",
    "tops": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=1200&h=300&fit=crop",
    "bottoms": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=1200&h=300&fit=crop",
    "dresses": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=1200&h=300&fit=crop",
    "outerwear": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=1200&h=300&fit=crop",
    "accessories": "https://images.unsplash.com/photo-1523779105320-d1cd346ff52b?w=1200&h=300&fit=crop",
    "footwear": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=1200&h=300&fit=crop",
}

# Map product categories to Nova Canvas garment classes
CATEGORY_TO_GARMENT_CLASS = {
    "tops": "UPPER_BODY",
    "outerwear": "UPPER_BODY",
    "bottoms": "LOWER_BODY",
    "dresses": "FULL_BODY",
    "accessories": "UPPER_BODY",
    "footwear": "FOOTWEAR",
}

# Map product IDs to categories for try-on garment class lookup
PRODUCT_CATEGORIES = {}  # populated at runtime from DynamoDB


def download_image_as_base64(url):
    """Download an image from URL and return as base64 string."""
    import requests
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return base64.b64encode(resp.content).decode("utf-8")


def resize_image_for_nova(image_bytes, max_pixels=4_100_000):
    """Resize image to fit Nova Canvas limits (max 4.1M pixels, max 2048 on any side)."""
    from PIL import Image
    img = Image.open(BytesIO(image_bytes))
    # Convert RGBA to RGB if needed
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    # Ensure no side exceeds 2048
    img.thumbnail((2048, 2048))
    # Further shrink if total pixels exceed limit
    w, h = img.size
    if w * h > max_pixels:
        scale = (max_pixels / (w * h)) ** 0.5
        img = img.resize((int(w * scale), int(h * scale)))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def virtual_try_on(user_photo_bytes, product_image_url, garment_class="UPPER_BODY"):
    """Use Amazon Nova Canvas VIRTUAL_TRY_ON to overlay a product onto the user's photo."""
    from botocore.config import Config
    sess = boto3.Session(profile_name=PROFILE, region_name=REGION) if PROFILE else boto3.Session(region_name=REGION)
    bedrock = sess.client(
        "bedrock-runtime",
        region_name=REGION,
        config=Config(read_timeout=300),
    )

    source_b64 = resize_image_for_nova(user_photo_bytes)

    # Download and resize reference image too
    import requests as _req
    ref_resp = _req.get(product_image_url, timeout=15)
    ref_resp.raise_for_status()
    ref_b64 = resize_image_for_nova(ref_resp.content)

    inference_params = {
        "taskType": "VIRTUAL_TRY_ON",
        "virtualTryOnParams": {
            "sourceImage": source_b64,
            "referenceImage": ref_b64,
            "maskType": "GARMENT",
            "garmentBasedMask": {"garmentClass": garment_class},
        },
    }

    body_json = json.dumps(inference_params)
    response = bedrock.invoke_model(
        modelId="amazon.nova-canvas-v1:0",
        body=body_json,
        accept="application/json",
        contentType="application/json",
    )

    result = json.loads(response["body"].read())
    if result.get("images"):
        return base64.b64decode(result["images"][0])
    return None


@st.cache_resource
def get_dynamodb():
    if PROFILE:
        session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    else:
        session = boto3.Session(region_name=REGION)
    ssm = session.client("ssm", region_name=REGION)
    product_table_name = ssm.get_parameter(Name="/app/retailshopping/dynamodb/product_table_name")["Parameter"]["Value"]
    customer_table_name = ssm.get_parameter(Name="/app/retailshopping/dynamodb/customer_table_name")["Parameter"]["Value"]
    cart_table_name = ssm.get_parameter(Name="/app/retailshopping/dynamodb/cart_table_name")["Parameter"]["Value"]
    dynamodb = session.resource("dynamodb", region_name=REGION)
    return {
        "products": dynamodb.Table(product_table_name),
        "customers": dynamodb.Table(customer_table_name),
        "cart": dynamodb.Table(cart_table_name),
    }


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


def load_products():
    tables = get_dynamodb()
    resp = tables["products"].scan()
    return decimal_to_float(resp.get("Items", []))


def load_cart(customer_id="CUST-001"):
    tables = get_dynamodb()
    resp = tables["cart"].query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("customer_id").eq(customer_id)
    )
    return decimal_to_float(resp.get("Items", []))


def add_to_cart_db(customer_id, product, size, quantity=1):
    import uuid
    tables = get_dynamodb()
    from datetime import datetime
    cart_item_id = f"CI-{uuid.uuid4().hex[:8].upper()}"
    tables["cart"].put_item(Item={
        "customer_id": customer_id,
        "cart_item_id": cart_item_id,
        "product_id": product["product_id"],
        "product_name": product["name"],
        "brand": product["brand"],
        "size": size,
        "quantity": quantity,
        "price": Decimal(str(product["price"])),
        "added_at": datetime.utcnow().isoformat(),
    })
    return cart_item_id


def remove_from_cart_db(customer_id, cart_item_id):
    tables = get_dynamodb()
    tables["cart"].delete_item(Key={"customer_id": customer_id, "cart_item_id": cart_item_id})


# --- Page Config ---
st.set_page_config(
    page_title="StyleHub - Multi-Brand Clothing Store",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 16px;
        background: white;
        transition: box-shadow 0.2s;
    }
    .product-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .price-tag {
        font-size: 1.4em;
        font-weight: 700;
        color: #e63946;
    }
    .brand-tag {
        font-size: 0.85em;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .rating-stars {
        color: #ffc107;
    }
    .category-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        background: #f0f0f0;
        font-size: 0.8em;
        margin-right: 4px;
    }
    .cart-badge {
        background: #e63946;
        color: white;
        border-radius: 50%;
        padding: 2px 8px;
        font-size: 0.8em;
        font-weight: bold;
    }
    .hero-banner {
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 24px;
    }
    div[data-testid="stChatMessage"] {
        background: #f8f9fa;
        border-radius: 12px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if "cart_count" not in st.session_state:
    st.session_state.cart_count = 0
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "selected_product" not in st.session_state:
    st.session_state.selected_product = None

# --- Sidebar (rendered first, before any data loading) ---
NAV_OPTIONS = ["🏪 Shop", "🛒 Cart", "🤖 Shopping Assistant"]

if "default_nav_index" not in st.session_state:
    st.session_state.default_nav_index = 0

with st.sidebar:
    st.markdown("## 🛍️ StyleHub")
    st.markdown("*Your Multi-Brand Fashion Destination*")
    st.divider()

    page = st.radio(
        "Navigate",
        NAV_OPTIONS,
        index=st.session_state.default_nav_index,
        key="nav_radio",
        label_visibility="collapsed",
    )

    st.session_state.default_nav_index = NAV_OPTIONS.index(page)

    st.divider()
    cart_badge_placeholder = st.empty()

# Determine current page directly from radio value
if "Shopping Assistant" in page:
    current_page = "assistant"
elif "Cart" in page:
    current_page = "cart"
else:
    current_page = "shop"

# Always load cart count so sidebar stays in sync
try:
    cart_items = load_cart()
    st.session_state.cart_count = len(cart_items)
except Exception:
    pass

# Update sidebar cart badge now that count is fresh
with st.sidebar:
    with cart_badge_placeholder:
        if st.session_state.cart_count > 0:
            st.markdown(f"🛒 **Cart:** {st.session_state.cart_count} item(s)")
        else:
            st.markdown("🛒 Cart is empty")

# Only load full product data when needed (not on assistant page)
products = []
brands = []

if current_page in ("shop", "cart"):
    try:
        products = load_products()
    except Exception as _db_err:
        if "db_error" not in st.session_state:
            st.session_state.db_error = str(_db_err)

    if products:
        brands = sorted(set(p["brand"] for p in products))
        with st.sidebar:
            st.divider()
            st.markdown("**Brands**")
            for b in brands:
                st.markdown(f"• {b}")


# ===================== SHOP PAGE =====================
if current_page == "shop":

    if not products:
        st.markdown("# 🛍️ StyleHub")
        st.error("Could not load products. Please check your AWS credentials and DynamoDB tables.")
        if "db_error" in st.session_state:
            st.code(st.session_state.db_error)
        st.stop()

    if st.session_state.selected_product:
        # --- Product Detail View ---
        prod = st.session_state.selected_product
        if st.button("← Back to Shop"):
            st.session_state.selected_product = None
            st.rerun()

        col_img, col_info = st.columns([1, 1])
        with col_img:
            img_url = PRODUCT_IMAGES.get(prod["product_id"], "https://via.placeholder.com/400x500")
            st.image(img_url, use_container_width=True)

        with col_info:
            st.markdown(f'<span class="brand-tag">{prod["brand"]}</span>', unsafe_allow_html=True)
            st.markdown(f"## {prod['name']}")
            st.markdown(f'<span class="price-tag">${prod["price"]:.2f}</span>', unsafe_allow_html=True)

            stars = "⭐" * int(prod.get("rating", 0))
            st.markdown(f"{stars} ({prod.get('reviews_count', 0)} reviews)")
            st.markdown(f"**Material:** {prod.get('material', 'N/A')}")
            st.markdown(f"**Gender:** {prod.get('gender', 'unisex').title()}")
            st.divider()
            st.markdown(prod.get("description", ""))
            st.divider()

            sizes = prod.get("sizes", {})
            available = [s for s, q in sizes.items() if (isinstance(q, (int, float)) and q > 0)]

            if available:
                selected_size = st.selectbox("Select Size", available)
                stock = int(sizes.get(selected_size, 0))
                st.caption(f"{stock} in stock")

                if st.button("🛒 Add to Cart", type="primary", use_container_width=True):
                    add_to_cart_db("CUST-001", prod, selected_size)
                    st.success(f"Added {prod['name']} (Size {selected_size}) to cart!")
                    st.session_state.cart_count += 1
                    st.rerun()
            else:
                st.warning("Out of stock")

            if prod.get("colors"):
                st.markdown("**Available Colors:** " + ", ".join(prod["colors"]))

    else:
        # --- Product Listing by Category ---
        st.markdown("# 🛍️ StyleHub")
        st.markdown("*Discover fashion from top brands, all in one place*")

        # Filters row
        col_filters = st.columns([1, 1, 1])
        with col_filters[0]:
            selected_brand = st.selectbox("Brand", ["all"] + (brands if brands else []))
        with col_filters[1]:
            selected_gender = st.selectbox("Gender", ["all", "men", "women", "unisex"])
        with col_filters[2]:
            sort_by = st.selectbox("Sort", ["Featured", "Price: Low to High", "Price: High to Low", "Rating"])

        # Banner
        st.image(CATEGORY_BANNERS["all"], use_container_width=True)

        # Filter
        filtered = products
        if selected_brand != "all":
            filtered = [p for p in filtered if p["brand"] == selected_brand]
        if selected_gender != "all":
            filtered = [p for p in filtered if p.get("gender", "unisex") in (selected_gender, "unisex")]

        # Sort
        if sort_by == "Price: Low to High":
            filtered.sort(key=lambda p: p["price"])
        elif sort_by == "Price: High to Low":
            filtered.sort(key=lambda p: p["price"], reverse=True)
        elif sort_by == "Rating":
            filtered.sort(key=lambda p: p.get("rating", 0), reverse=True)

        st.markdown(f"**{len(filtered)} products found**")

        # Group by category
        category_order = ["tops", "bottoms", "dresses", "footwear", "accessories", "outerwear"]
        cats_in_data = sorted(set(p["category"] for p in filtered))
        ordered_cats = [c for c in category_order if c in cats_in_data] + [c for c in cats_in_data if c not in category_order]

        CATEGORY_EMOJI = {
            "tops": "👕", "bottoms": "👖", "dresses": "👗",
            "footwear": "👟", "accessories": "👜", "outerwear": "🧥",
        }

        for cat in ordered_cats:
            cat_products = [p for p in filtered if p["category"] == cat]
            if not cat_products:
                continue

            emoji = CATEGORY_EMOJI.get(cat, "🏷️")
            st.markdown(f"### {emoji} {cat.title()}")

            # Horizontal scrollable row using st.columns
            num_visible = min(len(cat_products), 5)
            cols = st.columns(num_visible)
            for idx, prod in enumerate(cat_products[:num_visible]):
                with cols[idx]:
                    img_url = PRODUCT_IMAGES.get(prod["product_id"], "https://via.placeholder.com/400x500")
                    st.image(img_url, use_container_width=True)
                    st.markdown(f'<span class="brand-tag">{prod["brand"]}</span>', unsafe_allow_html=True)
                    st.markdown(f"**{prod['name']}**")
                    st.markdown(f'<span class="price-tag">${prod["price"]:.2f}</span>', unsafe_allow_html=True)
                    stars = "⭐" * int(prod.get("rating", 0))
                    st.caption(f"{stars} ({prod.get('reviews_count', 0)} reviews)")
                    if st.button("View Details", key=f"view_{prod['product_id']}"):
                        st.session_state.selected_product = prod
                        st.rerun()

            # Show remaining products in an expander if more than 5
            if len(cat_products) > 5:
                with st.expander(f"Show all {len(cat_products)} {cat.title()} products"):
                    extra_cols = st.columns(5)
                    for idx, prod in enumerate(cat_products[5:]):
                        with extra_cols[idx % 5]:
                            img_url = PRODUCT_IMAGES.get(prod["product_id"], "https://via.placeholder.com/400x500")
                            st.image(img_url, use_container_width=True)
                            st.markdown(f'<span class="brand-tag">{prod["brand"]}</span>', unsafe_allow_html=True)
                            st.markdown(f"**{prod['name']}**")
                            st.markdown(f'<span class="price-tag">${prod["price"]:.2f}</span>', unsafe_allow_html=True)
                            if st.button("View", key=f"view_{prod['product_id']}"):
                                st.session_state.selected_product = prod
                                st.rerun()

            st.divider()


# ===================== CART PAGE =====================
elif current_page == "cart":
    st.markdown("# 🛒 Your Cart")

    cart_items = load_cart()

    if not cart_items:
        st.info("Your cart is empty. Start shopping to add items!")
        if st.button("🛍️ Continue Shopping"):
            st.session_state.default_nav_index = 0
            st.rerun()
    else:
        subtotal = 0
        for item in cart_items:
            col_img, col_detail, col_action = st.columns([1, 3, 1])
            pid = item.get("product_id", "")
            img_url = PRODUCT_IMAGES.get(pid, "https://via.placeholder.com/100x120")

            with col_img:
                st.image(img_url, width=100)
            with col_detail:
                st.markdown(f"**{item['product_name']}**")
                st.caption(f"{item['brand']} | Size: {item['size']} | Qty: {item.get('quantity', 1)}")
                item_total = item["price"] * item.get("quantity", 1)
                st.markdown(f"${item_total:.2f}")
                subtotal += item_total
            with col_action:
                if st.button("🗑️", key=f"rm_{item['cart_item_id']}"):
                    remove_from_cart_db("CUST-001", item["cart_item_id"])
                    st.rerun()

            st.divider()

        # Order summary
        tax = round(subtotal * 0.08, 2)
        total = round(subtotal + tax, 2)

        st.markdown("### Order Summary")
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown(f"Subtotal: **${subtotal:.2f}**")
            st.markdown(f"Tax (8%): **${tax:.2f}**")
            st.markdown(f"### Total: ${total:.2f}")
        with col_r:
            payment = st.selectbox("Payment Method", ["credit_card", "debit_card", "upi", "wallet"])
            if st.button("💳 Proceed to Checkout", type="primary", use_container_width=True):
                # Create order via Lambda or direct DynamoDB
                import uuid
                from datetime import datetime
                tables = get_dynamodb()
                order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"
                tables_db = get_dynamodb()

                order_table_name = boto3.Session(
                    profile_name=PROFILE, region_name=REGION
                ).client("ssm").get_parameter(
                    Name="/app/retailshopping/dynamodb/order_table_name"
                )["Parameter"]["Value"] if PROFILE else boto3.Session(
                    region_name=REGION
                ).client("ssm").get_parameter(
                    Name="/app/retailshopping/dynamodb/order_table_name"
                )["Parameter"]["Value"]

                session_db = boto3.Session(profile_name=PROFILE, region_name=REGION) if PROFILE else boto3.Session(region_name=REGION)
                order_table = session_db.resource("dynamodb", region_name=REGION).Table(order_table_name)

                order_table.put_item(Item={
                    "order_id": order_id,
                    "customer_id": "CUST-001",
                    "items": [{
                        "product_name": i["product_name"],
                        "brand": i["brand"],
                        "size": i["size"],
                        "quantity": int(i.get("quantity", 1)),
                        "price": Decimal(str(i["price"])),
                    } for i in cart_items],
                    "subtotal": Decimal(str(subtotal)),
                    "tax": Decimal(str(tax)),
                    "total": Decimal(str(total)),
                    "payment_method": payment,
                    "status": "confirmed",
                    "created_at": datetime.utcnow().isoformat(),
                })

                # Clear cart
                for item in cart_items:
                    remove_from_cart_db("CUST-001", item["cart_item_id"])

                st.balloons()
                st.success(f"Order placed! Order ID: **{order_id}**")
                st.session_state.cart_count = 0


# ===================== ASSISTANT PAGE =====================
elif current_page == "assistant":
    st.markdown("# 🤖 Shopping Assistant")
    st.markdown("*Ask me anything about our products, get recommendations, or manage your cart!*")

    # Session state defaults
    if "agent_initialized" not in st.session_state:
        st.session_state.agent_initialized = False
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "agent_error" not in st.session_state:
        st.session_state.agent_error = None

    gateway_id = os.getenv("GATEWAY_ID", "retail-shopping-gw-bgg7utkdi2")

    def connect_agent():
        """Lazy agent initialization - called only when user sends first message."""
        if st.session_state.agent_initialized:
            return True
        try:
            from strands.models import BedrockModel
            from mcp.client.streamable_http import streamablehttp_client
            from strands.tools.mcp.mcp_client import MCPClient
            from strands import Agent
            import utils as agent_utils

            boto_session, agentcore_client = agent_utils.create_agentcore_client()
            gateway_endpoint = agent_utils.get_gateway_endpoint(agentcore_client, gateway_id)
            jwt_token = agent_utils.get_oath_token(boto_session)

            mcp_client = MCPClient(
                lambda: streamablehttp_client(
                    gateway_endpoint,
                    headers={"Authorization": f"Bearer {jwt_token}"},
                )
            )

            bedrock_model = BedrockModel(
                model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
                temperature=0.7,
                streaming=True,
                boto_session=boto_session,
            )

            system_prompt = """You are a friendly shopping assistant for StyleHub, a multi-brand clothing store.
Customer CUST-001 (Priya Sharma) is logged in. Always use customer_id "CUST-001" for all cart and checkout operations.

CRITICAL WORKFLOW RULES:
- NEVER ask the user for product IDs, cart item IDs, or any internal identifiers.
- When a user mentions a product by name, brand, or description, ALWAYS use the searchProducts tool first to find matching products and get their product_id.
- When adding to cart, use the product_id from search results. If the user hasn't specified a size, show available sizes and ask which one they want.
- When removing from cart, first call getCart to find the cart_item_id, then use removeFromCart.
- When checking out, use customer_id "CUST-001" and ask only for payment method (credit_card, debit_card, upi, wallet).

TOOL USAGE:
- searchProducts: Use query, category, brand, gender, min_price, max_price, size parameters. Call this whenever the user asks about products.
- getProductDetails: Use the product_id from search results to get full details. The user should never need to provide this.
- addToCart: Requires customer_id ("CUST-001"), product_id (from search), and size. Get product_id by searching first.
- getCart: Use customer_id "CUST-001" to view cart.
- removeFromCart: Requires customer_id and cart_item_id (get from getCart results).
- checkout: Requires customer_id "CUST-001" and payment_method.

PRODUCT IMAGES:
- When showing product details or search results, ALWAYS include the image tag [IMG:PROD-XXX] (using the actual product_id) right after the product name.
- Example: "**Classic White T-Shirt** [IMG:PROD-001] by UrbanThreads - $29.99"
- This tag will be rendered as an actual product image in the UI. Always include it for every product you mention.
- Place the tag on its own line if listing multiple products, right after each product name.

RESPONSE STYLE:
- Be concise and friendly. Format product info clearly with name, brand, price, and available sizes.
- Never expose internal IDs (product_id, customer_id, cart_item_id) to the user in plain text. Only use them inside [IMG:PROD-XXX] tags.
- Use emojis sparingly.
"""

            mcp_client.__enter__()
            tools = mcp_client.list_tools_sync()
            agent = Agent(model=bedrock_model, tools=tools, system_prompt=system_prompt)

            st.session_state.agent = agent
            st.session_state.mcp_client = mcp_client
            st.session_state.agent_initialized = True
            st.session_state.agent_error = None
            return True

        except Exception as e:
            st.session_state.agent_error = str(e)
            return False

    # Show connection status
    if st.session_state.agent_initialized:
        st.success("🟢 Assistant connected")
    elif st.session_state.agent_error:
        st.warning(f"⚠️ Connection issue: {st.session_state.agent_error}")
        if st.button("🔄 Retry Connection"):
            st.session_state.agent_error = None
            st.session_state.agent_initialized = False
            st.rerun()
    else:
        st.info("💬 Type a message below to start chatting. The assistant will connect automatically.")

    st.divider()

    # --- Polly TTS helper ---
    import re

    def synthesize_speech(text):
        """Convert text to speech using Amazon Polly neural voice."""
        sess = boto3.Session(profile_name=PROFILE, region_name=REGION) if PROFILE else boto3.Session(region_name=REGION)
        polly = sess.client("polly", region_name=REGION)
        clean = re.sub(r'[*_#`\[\]()]', '', text)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if len(clean) > 2900:
            clean = clean[:2900] + "... and more."
        if not clean:
            return None
        resp = polly.synthesize_speech(Text=clean, OutputFormat="mp3", VoiceId="Joanna", Engine="neural")
        return resp["AudioStream"].read()

    # --- Unified chat with voice input ---
    from streamlit_js_eval import streamlit_js_eval

    if "auto_read_aloud" not in st.session_state:
        st.session_state.auto_read_aloud = True
    if "last_polly_audio" not in st.session_state:
        st.session_state.last_polly_audio = None

    # Quick action buttons
    st.markdown("**Quick Actions:**")
    qcols = st.columns(4)
    quick_prompts = [
        "Show me all products",
        "What's trending for women?",
        "Show my cart",
        "Find jackets under $100",
    ]
    for i, qp in enumerate(quick_prompts):
        with qcols[i]:
            if st.button(qp, key=f"quick_{i}", use_container_width=True):
                st.session_state.chat_messages.append({"role": "user", "content": qp})
                st.session_state.pending_prompt = qp
                st.rerun()

    # Audio controls row
    audio_cols = st.columns([2, 1, 1])
    with audio_cols[0]:
        st.session_state.auto_read_aloud = st.toggle("🔊 Auto read aloud", value=st.session_state.auto_read_aloud)
    with audio_cols[1]:
        if st.button("⏹️ Stop Reading", key="stop_audio"):
            streamlit_js_eval(js_expressions="document.querySelectorAll('audio').forEach(a => { a.pause(); a.currentTime = 0; }); 'stopped'", key="stop_js")
    with audio_cols[2]:
        if st.session_state.last_polly_audio and st.button("🔁 Replay", key="replay_audio"):
            st.audio(st.session_state.last_polly_audio, format="audio/mp3", autoplay=True)

    st.divider()

    # --- Render chat message with inline product images ---
    import re as _re

    def render_message_with_images(text, show_tryon_buttons=False):
        """Parse [IMG:PROD-XXX] tags and render text + product images inline."""
        parts = _re.split(r'(\[IMG:PROD-\d+\])', text)
        for part in parts:
            match = _re.match(r'\[IMG:(PROD-\d+)\]', part)
            if match:
                pid = match.group(1)
                img_url = PRODUCT_IMAGES.get(pid)
                if img_url:
                    st.image(img_url, width=250)
                    if show_tryon_buttons:
                        if st.button(f"👗 Try this on", key=f"tryon_{pid}_{id(text)}"):
                            st.session_state.tryon_product_id = pid
                            st.rerun()
            else:
                stripped = part.strip()
                if stripped:
                    st.markdown(stripped)

    # Extract product IDs mentioned in the last assistant message (for try-on)
    if "tryon_product_id" not in st.session_state:
        st.session_state.tryon_product_id = None
    if "tryon_result" not in st.session_state:
        st.session_state.tryon_result = None

    # Chat message history
    for idx, msg in enumerate(st.session_state.chat_messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                # Show try-on buttons only on the last assistant message
                is_last_assistant = idx == max(
                    (i for i, m in enumerate(st.session_state.chat_messages) if m["role"] == "assistant"),
                    default=-1,
                )
                render_message_with_images(msg["content"], show_tryon_buttons=is_last_assistant)
            else:
                st.markdown(msg["content"])

    # --- Voice input via streamlit_js_eval (runs in main page, not iframe) ---
    if "voice_listening" not in st.session_state:
        st.session_state.voice_listening = False

    # Mic button row
    mic_col, spacer_col = st.columns([1, 5])
    with mic_col:
        if st.button("🎤 Speak", key="mic_btn"):
            st.session_state.voice_listening = True
            st.rerun()

    # If mic was clicked, run speech recognition via JS in main page context
    if st.session_state.voice_listening:
        st.info("🔴 Listening... speak now (Chrome/Edge required)")
        transcript = streamlit_js_eval(
            js_expressions="""
            new Promise((resolve, reject) => {
                const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SR) { resolve('__ERROR__:Web Speech API not supported'); return; }
                const rec = new SR();
                rec.lang = 'en-US';
                rec.interimResults = false;
                rec.continuous = false;
                rec.maxAlternatives = 1;
                rec.onresult = (e) => {
                    let text = '';
                    for (let i = 0; i < e.results.length; i++) {
                        text += e.results[i][0].transcript;
                    }
                    resolve(text.trim());
                };
                rec.onerror = (e) => { resolve('__ERROR__:' + e.error); };
                rec.onend = () => { /* if no result, onerror or onresult already fired */ };
                rec.start();
            })
            """,
            key="voice_recognition",
        )

        if transcript is not None:
            st.session_state.voice_listening = False
            if transcript.startswith("__ERROR__:"):
                error = transcript.replace("__ERROR__:", "")
                if error == "no-speech":
                    st.warning("No speech detected. Try again.")
                else:
                    st.error(f"Speech error: {error}")
            elif transcript.strip():
                st.session_state.chat_messages.append({"role": "user", "content": transcript.strip()})
                st.session_state.pending_prompt = transcript.strip()
                st.rerun()

    # Process pending prompt (from quick action or voice)
    pending = st.session_state.pop("pending_prompt", None)

    # Native chat input for typing
    prompt = st.chat_input("Type your message here...")

    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        active_prompt = prompt
    elif pending:
        active_prompt = pending
    else:
        active_prompt = None

    if active_prompt:
        with st.chat_message("assistant"):
            if not st.session_state.agent_initialized:
                with st.spinner("Connecting to assistant..."):
                    connected = connect_agent()
                if not connected:
                    error_msg = f"Could not connect: {st.session_state.agent_error}. Please check your Gateway ID and credentials."
                    st.error(error_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
                    st.rerun()

            if st.session_state.agent_initialized:
                with st.spinner("Thinking..."):
                    try:
                        result = st.session_state.agent(active_prompt)
                        response_text = str(result)
                        if hasattr(result, "message") and hasattr(result.message, "content"):
                            for block in result.message.content:
                                if hasattr(block, "text"):
                                    response_text = block.text
                                    break
                        render_message_with_images(response_text, show_tryon_buttons=True)
                        st.session_state.chat_messages.append({"role": "assistant", "content": response_text})

                        # Auto read aloud with Polly
                        if st.session_state.auto_read_aloud and response_text:
                            try:
                                audio_bytes = synthesize_speech(response_text)
                                if audio_bytes:
                                    st.session_state.last_polly_audio = audio_bytes
                                    st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                            except Exception:
                                pass  # Silently skip TTS on error
                    except Exception as e:
                        error_msg = f"Sorry, I encountered an error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})

    # ===================== VIRTUAL TRY-ON PANEL =====================
    if st.session_state.tryon_product_id:
        pid = st.session_state.tryon_product_id
        product_img_url = PRODUCT_IMAGES.get(pid)

        st.divider()
        st.markdown("### 👗 Virtual Try-On")
        st.markdown(f"*Selected product: {pid}*")

        if product_img_url:
            tryon_cols = st.columns([1, 1, 1])
            with tryon_cols[0]:
                st.markdown("**Product Image**")
                st.image(product_img_url, width=250)

            with tryon_cols[1]:
                st.markdown("**Upload Your Photo**")
                uploaded_photo = st.file_uploader(
                    "Upload a full-body or upper-body photo",
                    type=["jpg", "jpeg", "png"],
                    key="tryon_upload",
                )
                if uploaded_photo:
                    st.image(uploaded_photo, width=250, caption="Your photo")

                # Garment class selector
                garment_class = st.selectbox(
                    "What are you trying on?",
                    ["UPPER_BODY", "LOWER_BODY", "FULL_BODY", "FOOTWEAR"],
                    index=0,
                    key="tryon_garment_class",
                )

                btn_cols = st.columns(2)
                with btn_cols[0]:
                    run_tryon = st.button("✨ Try it on!", type="primary", disabled=not uploaded_photo)
                with btn_cols[1]:
                    if st.button("❌ Cancel"):
                        st.session_state.tryon_product_id = None
                        st.session_state.tryon_result = None
                        st.rerun()

            with tryon_cols[2]:
                st.markdown("**Result**")
                if run_tryon and uploaded_photo:
                    with st.spinner("Generating your look with Nova Canvas... (10-20 seconds)"):
                        try:
                            result_bytes = virtual_try_on(
                                uploaded_photo.getvalue(),
                                product_img_url,
                                garment_class=garment_class,
                            )
                            if result_bytes:
                                st.session_state.tryon_result = result_bytes
                                st.image(result_bytes, width=350, caption="Virtual Try-On Result")
                                st.success("Try-on complete!")
                            else:
                                st.error("Nova Canvas did not return an image. Try a different photo.")
                        except Exception as e:
                            err_msg = str(e)
                            st.error(f"Try-on failed: {err_msg}")
                            if "AccessDeniedException" in err_msg:
                                st.warning("Make sure Amazon Nova Canvas (amazon.nova-canvas-v1:0) is enabled in your Bedrock Model Access settings.")
                            elif "ReadTimeoutError" in err_msg or "timed out" in err_msg.lower():
                                st.warning("The request timed out. Try uploading a smaller photo.")
                elif st.session_state.tryon_result:
                    st.image(st.session_state.tryon_result, width=350, caption="Virtual Try-On Result")
                else:
                    st.info("Upload your photo and click 'Try it on!' to see the result here.")
        else:
            st.warning("Product image not found for this product.")
            if st.button("Close"):
                st.session_state.tryon_product_id = None
                st.rerun()
