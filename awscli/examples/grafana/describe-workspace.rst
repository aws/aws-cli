**To describe a Grafana workspace**

The following ``describe-workspace`` example retrieves detailed information about a specific Grafana workspace. ::

    aws grafana describe-workspace \
        --workspace-id g-1234567890

Output::

    {
        "workspace": {
            "id": "g-1234567890",
            "name": "MyGrafanaWorkspace",
            "description": "Development team monitoring workspace",
            "endpoint": "https://g-1234567890.grafana-workspace.us-east-1.amazonaws.com",
            "status": "ACTIVE",
            "created": "2023-05-07T20:21:01.656000+00:00",
            "modified": "2023-05-07T20:25:15.123000+00:00",
            "accountAccessType": "CURRENT_ACCOUNT",
            "authenticationProviders": ["AWS_SSO"],
            "permissionType": "SERVICE_MANAGED",
            "grafanaVersion": "9.4",
            "dataSources": ["CLOUDWATCH"],
            "organizationRoleName": "ADMIN",
            "stackSetName": "grafana-workspace-stack",
            "workspaceRoleArn": "arn:aws:iam::123456789012:role/service-role/AmazonGrafanaServiceRole-g1234567890"
        }
    }
