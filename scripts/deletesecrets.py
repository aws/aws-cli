import boto3


def delete_all_secrets():
    # Create Secrets Manager client
    session = boto3.session.Session()
    client = session.client('secretsmanager')

    try:
        # List all secrets
        paginator = client.get_paginator('list_secrets')
        for page in paginator.paginate():
            for secret in page['SecretList']:
                secret_name = secret['Name']

                # Delete secret without recovery window
                client.delete_secret(
                    SecretId=secret_name,
                    ForceDeleteWithoutRecovery=True
                )
                print(f"Deleted secret: {secret_name}")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    delete_all_secrets()