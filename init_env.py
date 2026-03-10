"""
Sets up environment variables from CloudFormation outputs and OAuth discovery endpoint.
Creates a .env file used by other scripts.
"""
import boto3
import os
import argparse
import requests

parser = argparse.ArgumentParser(
    prog="setup_env_variables",
    description="Setup environment variables for Retail Shopping Agent",
)
parser.add_argument("--cfn_name", help="CloudFormation stack name", required=True)
parser.add_argument("--region", default="us-east-1", help="AWS region")
parser.add_argument(
    "--openapi_spec_file",
    default="./retail-openapi-spec.yaml",
    help="Path to OpenAPI spec file",
)
parser.add_argument("--profile", help="AWS credentials profile name (optional)")


def main():
    apigateway_endpoint = ""

    env_vars = {
        "aws_default_region": args.region,
        "gateway_iam_role": "",
        "cognito_discovery_url": "",
        "cognito_issuer": "",
        "cognito_auth_endpoint": "",
        "cognito_token_url": "",
        "cognito_user_pool_id": "",
        "cognito_client_id": "",
        "cognito_auth_scope": "",
        "openapi_spec_file": args.openapi_spec_file,
    }

    if args.profile:
        session = boto3.Session(profile_name=args.profile)
        env_vars["awscred_profile_name"] = args.profile
    else:
        session = boto3.Session()

    print(f"Getting outputs from CloudFormation stack: {args.cfn_name}")
    cfn_client = session.client("cloudformation", region_name=args.region)

    response = cfn_client.describe_stacks(StackName=args.cfn_name)

    cfn_output = []
    for stack in response["Stacks"]:
        if stack["StackName"] == args.cfn_name:
            cfn_output = stack.get("Outputs", [])

    output_map = {
        "IAMRoleArn": "gateway_iam_role",
        "oAuthDiscoveryURL": "cognito_discovery_url",
        "oAuthIssuer": "cognito_issuer",
        "oAuthEndpoint": "cognito_auth_endpoint",
        "oAuthTokenURL": "cognito_token_url",
        "APIClientId": "cognito_client_id",
        "oAuthScope": "cognito_auth_scope",
        "UserPoolId": "cognito_user_pool_id",
        "ApiUrl": None,  # handled separately
    }

    for output in cfn_output:
        key = output["OutputKey"]
        if key == "ApiUrl":
            apigateway_endpoint = output["OutputValue"]
        elif key in output_map and output_map[key]:
            env_vars[output_map[key]] = output["OutputValue"]

    # Fetch OAuth metadata from discovery endpoint
    discovery_url = env_vars.get("cognito_discovery_url", "")
    if discovery_url:
        print(f"Fetching OAuth metadata from: {discovery_url}")
        resp = requests.get(discovery_url)
        metadata = resp.json()
        if "authorization_endpoint" in metadata:
            env_vars["cognito_auth_endpoint"] = metadata["authorization_endpoint"]
        if "issuer" in metadata:
            env_vars["cognito_issuer"] = metadata["issuer"]

    with open(".env", "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    print(".env file created successfully.")
    print(f"API Endpoint: {apigateway_endpoint}")
    print("Update your OpenAPI spec with this endpoint URL.")


if __name__ == "__main__":
    args = parser.parse_args()

    if args.region not in ("us-east-1", "us-west-2"):
        raise Exception("Only us-east-1 and us-west-2 are supported")

    if not os.path.exists(args.openapi_spec_file):
        raise Exception(f"OpenAPI spec file not found: {args.openapi_spec_file}")

    main()
