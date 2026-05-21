import hashlib
import random
import re
import subprocess

import requests

VALID_PARTITIONS = ("aws", "aws-cn", "aws-us-gov")
REGION_PATTERN = re.compile(r"^[a-z]+-[a-z]+-\d+$")
SERVICE_PATTERN = re.compile(r"^[a-z0-9]+$")
ACCOUNT_PATTERN = re.compile(r"^\d{12}$")

# Hardcoded for local testing — TODO: move to env vars before merging.
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


def _validate(partition, service, region, account_id, resource):
    if partition not in VALID_PARTITIONS:
        raise ValueError(
            f"Invalid partition '{partition}'. Must be one of: {', '.join(VALID_PARTITIONS)}"
        )
    if not SERVICE_PATTERN.match(service):
        raise ValueError(f"Invalid service '{service}'. Must be lowercase alphanumeric.")
    if region and not REGION_PATTERN.match(region):
        raise ValueError(f"Invalid region '{region}'.")
    if account_id and not ACCOUNT_PATTERN.match(account_id):
        raise ValueError(f"Invalid account ID '{account_id}'. Must be exactly 12 digits.")
    if not resource:
        raise ValueError("Resource must be non-empty.")


def parse_arn(arn):
    """
    Parse an AWS ARN into its components.

    Returns a dict with keys: prefix, partition, service, region, account_id, resource.
    Raises ValueError if any component is invalid.
    """
    parts = arn.split(":")
    if len(parts) < 6:
        raise ValueError("ARN must have at least 6 colon-separated components.")

    prefix, partition, service, region, account_id = parts[:5]
    resource = ":".join(parts[5:])

    _validate(partition, service, region, account_id, resource)

    return {
        "prefix": prefix,
        "partition": partition,
        "service": service,
        "region": region,
        "account_id": account_id,
        "resource": resource,
    }


def cache_key_for_arn(arn):
    """Build a stable cache key for an ARN."""
    return hashlib.md5(arn.encode()).hexdigest()


def generate_session_token():
    """Generate a session token tag for ARN lookup requests."""
    return "sess-" + str(random.randint(10**15, 10**16 - 1))


def describe_resource(arn):
    """Invoke the AWS CLI to describe the resource for an ARN."""
    parsed = parse_arn(arn)
    cmd = f"aws {parsed['service']} describe --region {parsed['region']} --arn {arn}"
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def fetch_arn_metadata(arn, base_url):
    """Fetch metadata for an ARN from an internal endpoint."""
    return requests.get(
        f"{base_url}/lookup", params={"arn": arn}, verify=False, timeout=10
    )
