from langchain_aws import ChatBedrock
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import asyncio
import argparse
import os
import utils

parser = argparse.ArgumentParser(
    prog="retail_langgraph_agent",
    description="Retail Shopping Assistant Agent (LangGraph) with MCP Gateway",
)
parser.add_argument("--gateway_id", help="Gateway Id", required=True)

(boto_session, agentcore_client) = utils.create_agentcore_client()

systemPrompt = """
You are a friendly and helpful shopping assistant for a multi-brand clothing store.
A customer with id CUST-001 has logged in.

You can help the customer with:
1/ Searching and browsing products by category, brand, size, price range, or keyword
2/ Viewing detailed product information (sizes, colors, stock availability)
3/ Adding products to their shopping cart
4/ Viewing and managing their cart
5/ Processing checkout and payment

Guidelines:
- Start by greeting the customer by name (look up their profile using the tools).
- Never expose internal IDs (product_id, customer_id) in your responses.
- When showing products, present them in a clean readable format with name, brand, price, and available sizes.
- When adding to cart, confirm the product name, size, and price with the customer first.
- During checkout, summarize the order with itemized totals before confirming.
- Be proactive: suggest related items or popular picks when appropriate.
- If a product is out of stock in the requested size, suggest alternative sizes or similar products.
"""


async def main(gateway_id):
    gateway_endpoint = utils.get_gateway_endpoint(
        agentcore_client=agentcore_client, gateway_id=gateway_id
    )
    print(f"Gateway Endpoint: {gateway_endpoint}")

    jwt_token = utils.get_oath_token(boto_session)

    client = MultiServerMCPClient(
        {
            "retail": {
                "url": gateway_endpoint,
                "transport": "streamable_http",
                "headers": {"Authorization": f"Bearer {jwt_token}"},
            }
        }
    )

    tools = await client.get_tools()

    model = ChatBedrock(
        model="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        beta_us=True,
    )

    agent = create_react_agent(model, tools, prompt=systemPrompt)
    history = ""

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

            history = history + "User: " + user_input
            response = await agent.ainvoke(
                {"messages": [{"role": "user", "content": history}]}
            )

            result = response["messages"][-1].content
            history = history + "\nAssistant: " + result + "\n"
            print(result)
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


if __name__ == "__main__":
    args = parser.parse_args()
    asyncio.run(main(args.gateway_id))
