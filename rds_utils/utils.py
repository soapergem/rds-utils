from typing import Any

import boto3
from botocore.session import Session


def format_parameters(parameters: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Transforms a dictionary of parameters into the format the RDS Data API requires.
    """
    transformed = []
    for name, value in parameters.items():
        if isinstance(value, (int, float)):
            transformed.append({"name": name, "value": {"doubleValue": value}})
        else:
            transformed.append({"name": name, "value": {"stringValue": value}})
    return transformed


def execute_query(
    session: Session,
    rds_endpoint_arn: str,
    secret_arn: str,
    database: str,
    query: str,
    parameters: dict[str, Any] = None,
):
    """
    Runs a SQL query using the RDS Data API, returning the raw boto3 response.
    """
    if not parameters:
        parameters = []
    else:
        parameters = format_parameters(parameters)

    rds_client = session.client("rds-data")
    response = rds_client.execute_statement(
        resourceArn=rds_endpoint_arn,
        secretArn=secret_arn,
        database=database,
        sql=query,
        parameters=parameters,
        includeResultMetadata=True,
    )

    return response


def fetch_query(
    session: Session,
    rds_endpoint_arn: str,
    secret_arn: str,
    database: str,
    query: str,
    parameters: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Runs a SQL query using the RDS Data API, returning the result set.
    """
    response = execute_query(
        session, rds_endpoint_arn, secret_arn, database, query, parameters
    )
    columns = [col.get("name") for col in response.get("columnMetadata")]
    rows = []

    for record in response.get("records"):
        row = dict(
            zip(
                columns,
                [col.get("doubleValue", col.get("stringValue")) for col in record],
            )
        )
        rows.append(row)

    return row


def get_xacct_session(
    session: Session,
    assume_role_arn: str,
) -> Session:
    """
    Instantiates a boto3 service within a secondary AWS account
    using assume-role. This is useful when an application living
    in account A needs to access an RDS instance living in account B.
    """
    sts_client = session.client("sts")
    response = sts_client.assume_role(
        RoleArn=assume_role_arn,
        RoleSessionName="rds-data",
    )
    credentials = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
