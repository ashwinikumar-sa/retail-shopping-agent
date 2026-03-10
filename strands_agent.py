from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient
from strands import Agent
import logging
import argparse
import os
import utils

parser = argparse.ArgumentParser(
    prog="retail_strands_agent",
    description="Retail Shopping Assistant Agent with MCP Gateway",
)
parser.add_argument("--gateway_id", help="Gateway Id", required=True)

os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"

(boto_session, agentcore_client) = utils.create_agentcore_client()

systemPrompt = """You are a friendly and helpful shopping assistant for a multi-brand clothing store.
Customer CUST-001 has logged in. Always use customer_id "CUST-001" for all cart and checkout operations.

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

RESPONSE STYLE:
- Start by greeting the customer by name (look up their profile using the tools).
- Never expose internal IDs (product_id, customer_id) in your responses.
- When showing products, present them in a clean readable format with name, brand, price, and available sizes.
- When adding to cart, confirm the product name, size, and price with the customer first.
- During checkout, summarize the order with itemized totals before confirming.
- Be proactive: suggest related items or popular picks when appropriate.
- If a product is out of stock in the requested size, suggest alternative sizes or similar products.
"""

if __name__ == "__main__":
    args = parser.parse_args()

    gateway_endpoint = utils.get_gateway_endpoint(
        agentcore_client=agentcore_client, gateway_id=args.gateway_id
    )
    print(f"Gateway Endpoint: {gateway_endpoint}")

    jwt_token = utils.get_oath_token(boto_session)
    client = MCPClient(
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

    logging.getLogger("strands").setLevel(logging.INFO)
    logging.basicConfig(
        format="%(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler()],
    )

    with client:
        tools = client.list_tools_sync()
        agent = Agent(
            model=bedrock_model, tools=tools, system_prompt=systemPrompt
        )

        print("=" * 60)
        print("🛍️  WELCOME TO YOUR SHOPPING ASSISTANT  🛍️")
        print("=" * 60)
        print("✨ I can help you with:")
        print("   🔍 Search & browse products")
        print("   🛒 Add items to your cart")
        print("   💳 Checkout & payment")
        print()
        print("🚪 Type 'exit' to quit anytime")
        print("=" * 60)
        print()

        while True:
            try:
                user_input = input("👤 You: ").strip()

                if not user_input:
                    print("💭 Please enter a message or type 'exit' to quit")
                    continue

                if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                    print()
                    print("=" * 40)
                    print("👋 Thanks for shopping with us!")
                    print("🎉 Have a great day!")
                    print("=" * 40)
                    break

                print("🤖 ShopBot: ", end="")
                agent(user_input)
                print()

            except KeyboardInterrupt:
                print()
                print("=" * 40)
                print("👋 Shopping session ended!")
                print("🎉 See you next time!")
                print("=" * 40)
                break
            except Exception as e:
                print(f"❌ An error occurred: {str(e)}")
                print("💡 Please try again or type 'exit' to quit")
                print()
