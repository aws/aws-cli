**To create a Grafana workspace**

The following ``create-workspace`` example creates a new Amazon Managed Grafana workspace with basic configuration. ::

    aws grafana create-workspace \
        --workspace-name "MyGrafanaWorkspace" \
        --workspace-description "Development team monitoring workspace" \
        --account-access-type CURRENT_ACCOUNT \
        --authentication-providers AWS_SSO \
        --permission-type SERVICE_MANAGED

Output::

    {
        "workspace": {
            "id": "g-1234567890",
            "name": "MyGrafanaWorkspace",
            "description": "Development team monitoring workspace",
            "endpoint": "https://g-1234567890.grafana-workspace.us-east-1.amazonaws.com",
            "status": "CREATING",
            "created": "2023-05-07T20:21:01.656000+00:00",
            "modified": "2023-05-07T20:21:01.656000+00:00",
            "accountAccessType": "CURRENT_ACCOUNT",
            "authenticationProviders": ["AWS_SSO"],
            "permissionType": "SERVICE_MANAGED",
            "grafanaVersion": "9.4"
        }
    }

**To create a workspace with custom data sources**

The following ``create-workspace`` example creates a Grafana workspace with specific data sources enabled. ::

    aws grafana create-workspace \
        --workspace-name "ProductionMonitoring" \
        --workspace-description "Production monitoring and alerting" \
        --account-access-type CURRENT_ACCOUNT \
        --authentication-providers AWS_SSO \
        --permission-type SERVICE_MANAGED \
        --workspace-data-sources CLOUDWATCH PROMETHEUS XRAY \
        --workspace-notification-destinations SNS

Output::

    {
        "workspace": {
            "id": "g-0987654321",
            "name": "ProductionMonitoring",
            "description": "Production monitoring and alerting",
            "endpoint": "https://g-0987654321.grafana-workspace.us-east-1.amazonaws.com",
            "status": "CREATING",
            "dataSources": ["CLOUDWATCH", "PROMETHEUS", "XRAY"],
            "notificationDestinations": ["SNS"]
        }
    }
