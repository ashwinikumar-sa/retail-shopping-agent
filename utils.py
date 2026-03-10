import httpx
import os
from dotenv import load_dotenv
import boto3
import requests

load_dotenv()


def create_agentcore_client():
    if os.getenv("awscred_profile_name") is None:
        boto_session = boto3.Session(region_name=os.getenv("aws_default_region"))
    else:
        boto_session = boto3.Session(
            profile_name=os.getenv("awscred_profile_name"),
            region_name=os.getenv("aws_default_region"),
        )

    agentcore_client = boto_session.client("bedrock-agentcore-control")
    return boto_session, agentcore_client


def create_http_client(**kwargs) -> httpx.AsyncClient:
    kwargs["verify"] = False
    kwargs.setdefault("timeout", httpx.Timeout(30.0))
    return httpx.AsyncClient(**kwargs)


def get_gateway_endpoint(agentcore_client, gateway_id):
    response = agentcore_client.get_gateway(gatewayIdentifier=gateway_id)
    return response["gatewayUrl"]


def list_gateways(agentcore_client):
    response = agentcore_client.list_gateways()
    return response["items"]


def get_oath_token(boto_session):
    response = requests.post(
        os.getenv("cognito_token_url"),
        data=(
            f"grant_type=client_credentials"
            f"&client_id={os.getenv('cognito_client_id')}"
            f"&client_secret={get_cognito_client_secret(boto_session)}"
            f"&scope={os.getenv('cognito_auth_scope')}"
        ),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return response.json()["access_token"]


def get_cognito_client_secret(boto_session):
    cognito_client = boto_session.client(
        "cognito-idp", region_name=os.getenv("aws_default_region")
    )
    response = cognito_client.describe_user_pool_client(
        UserPoolId=os.getenv("cognito_user_pool_id"),
        ClientId=os.getenv("cognito_client_id"),
    )
    return response["UserPoolClient"]["ClientSecret"]
