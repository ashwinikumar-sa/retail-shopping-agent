from dotenv import load_dotenv
import os
import json
import yaml
import argparse
import time
import utils
import botocore

load_dotenv()

parser = argparse.ArgumentParser(
    prog="setup_retail_mcp",
    description="Setup MCP gateway for Retail Shopping tools",
)
parser.add_argument("--op_type", help="Operation type: Create or Delete", required=True)
parser.add_argument("--gateway_name", help="Gateway name (required for Create)")
parser.add_argument("--gateway_id", help="Gateway ID (required for Delete)")

(boto_session, agentcore_client) = utils.create_agentcore_client()


def read_and_stringify_openapispec(yaml_file_path):
    try:
        with open(yaml_file_path, "r") as file:
            openapi_dict = yaml.safe_load(file)
            return str(json.dumps(openapi_dict))
    except FileNotFoundError:
        return f"Error: File {yaml_file_path} not found"
    except yaml.YAMLError as e:
        return f"Error parsing YAML: {str(e)}"


def create_gateway(gateway_name, gateway_desc):
    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [os.getenv("cognito_client_id")],
            "discoveryUrl": os.getenv("cognito_discovery_url"),
        }
    }

    search_config = {
        "mcp": {
            "searchType": "SEMANTIC",
            "supportedVersions": ["2025-03-26"],
        }
    }

    response = agentcore_client.create_gateway(
        name=gateway_name,
        roleArn=os.getenv("gateway_iam_role"),
        authorizerType="CUSTOM_JWT",
        description=gateway_desc,
        protocolType="MCP",
        authorizerConfiguration=auth_config,
        protocolConfiguration=search_config,
    )
    return response["gatewayId"]


def create_gatewaytarget(gateway_id, cred_provider_arn):
    openapi_spec = read_and_stringify_openapispec(os.getenv("openapi_spec_file"))

    credential_config = {
        "credentialProviderType": "OAUTH",
        "credentialProvider": {
            "oauthCredentialProvider": {
                "providerArn": cred_provider_arn,
                "scopes": [os.getenv("cognito_auth_scope")],
            }
        },
    }

    response = agentcore_client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="RetailTarget",
        description="Retail Shopping API Target",
        targetConfiguration={
            "mcp": {"openApiSchema": {"inlinePayload": openapi_spec}}
        },
        credentialProviderConfigurations=[credential_config],
    )
    return response["targetId"]


def delete_gatewaytarget(gateway_id):
    response = agentcore_client.list_gateway_targets(gatewayIdentifier=gateway_id)
    print(f"Found {len(response['items'])} targets for the gateway")

    for target in response["items"]:
        print(f"Deleting target: {target['name']} (ID: {target['targetId']})")
        agentcore_client.delete_gateway_target(
            gatewayIdentifier=gateway_id, targetId=target["targetId"]
        )


def delete_gateway(gateway_id):
    agentcore_client.delete_gateway(gatewayIdentifier=gateway_id)


def create_egress_oauth_provider(gateway_name):
    cred_provider_name = f"{gateway_name}-oauth-credential-provider"

    try:
        agentcore_client.delete_oauth2_credential_provider(name=cred_provider_name)
        print(f"Deleted existing credential provider: {cred_provider_name}")
        time.sleep(15)
    except botocore.exceptions.ClientError as err:
        if err.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    provider_config = {
        "customOauth2ProviderConfig": {
            "oauthDiscovery": {
                "authorizationServerMetadata": {
                    "issuer": os.getenv("cognito_issuer"),
                    "authorizationEndpoint": os.getenv("cognito_auth_endpoint"),
                    "tokenEndpoint": os.getenv("cognito_token_url"),
                    "responseTypes": ["token"],
                }
            },
            "clientId": os.getenv("cognito_client_id"),
            "clientSecret": utils.get_cognito_client_secret(boto_session),
        }
    }

    response = agentcore_client.create_oauth2_credential_provider(
        name=cred_provider_name,
        credentialProviderVendor="CustomOauth2",
        oauth2ProviderConfigInput=provider_config,
    )
    return response["credentialProviderArn"]


if __name__ == "__main__":
    args = parser.parse_args()

    if args.op_type.lower() not in ("create", "delete"):
        raise Exception("Operation type must be Create or Delete")

    if args.op_type.lower() == "create":
        if not args.gateway_name:
            raise Exception("Gateway name is required for Create")

        print(f"Creating gateway: {args.gateway_name}")
        gateway_id = create_gateway(args.gateway_name, args.gateway_name)
        print(f"Gateway created with ID: {gateway_id}")

        cred_arn = create_egress_oauth_provider(args.gateway_name)
        print("OAuth credential provider created.")

        target_id = create_gatewaytarget(gateway_id, cred_arn)
        print(f"Target created with ID: {target_id}")

    elif args.op_type.lower() == "delete":
        if not args.gateway_id:
            raise Exception("Gateway ID is required for Delete")

        print(f"Deleting targets for gateway: {args.gateway_id}")
        delete_gatewaytarget(args.gateway_id)
        print(f"Deleting gateway: {args.gateway_id}")
        delete_gateway(args.gateway_id)
        print("Gateway deleted.")
