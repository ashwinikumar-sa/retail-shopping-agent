"""
Populates DynamoDB tables with sample product catalog, customer, and cart data.
"""
import boto3
import os
import json
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

region = os.getenv("aws_default_region", "us-east-1")
profile = os.getenv("awscred_profile_name")

if profile:
    session = boto3.Session(profile_name=profile, region_name=region)
else:
    session = boto3.Session(region_name=region)

dynamodb = session.resource("dynamodb")


def load_json(path):
    with open(path, "r") as f:
        data = json.load(f, parse_float=Decimal)
    return data


def populate_table(table_name, items):
    table = dynamodb.Table(table_name)
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    print(f"Loaded {len(items)} items into {table_name}")


if __name__ == "__main__":
    products = load_json("test_data/products.json")
    customers = load_json("test_data/customers.json")

    # Get table names from SSM
    ssm = session.client("ssm", region_name=region)

    product_table = ssm.get_parameter(Name="/app/retailshopping/dynamodb/product_table_name")["Parameter"]["Value"]
    customer_table = ssm.get_parameter(Name="/app/retailshopping/dynamodb/customer_table_name")["Parameter"]["Value"]

    populate_table(product_table, products)
    populate_table(customer_table, customers)

    print("Test data loaded successfully.")
