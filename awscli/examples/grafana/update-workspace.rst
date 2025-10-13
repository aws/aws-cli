**To update a Grafana workspace**

The following ``update-workspace`` example updates the name and description of an existing Grafana workspace. ::

    aws grafana update-workspace \
        --workspace-id g-1234567890 \
        --workspace-name "UpdatedGrafanaWorkspace" \
        --workspace-description "Updated development team monitoring workspace"

Output::

    {
        "workspace": {
            "id": "g-1234567890",
            "name": "UpdatedGrafanaWorkspace",
            "description": "Updated development team monitoring workspace",
            "endpoint": "https://g-1234567890.grafana-workspace.us-east-1.amazonaws.com",
            "status": "UPDATING",
            "modified": "2023-05-07T21:30:45.789000+00:00"
        }
    }

**To update workspace data sources**

The following ``update-workspace`` example adds additional data sources to an existing workspace. ::

    aws grafana update-workspace \
        --workspace-id g-1234567890 \
        --workspace-data-sources CLOUDWATCH PROMETHEUS TIMESTREAM \
        --workspace-notification-destinations SNS SES

Output::

    {
        "workspace": {
            "id": "g-1234567890",
            "name": "UpdatedGrafanaWorkspace",
            "status": "UPDATING",
            "dataSources": ["CLOUDWATCH", "PROMETHEUS", "TIMESTREAM"],
            "notificationDestinations": ["SNS", "SES"],
            "modified": "2023-05-07T21:35:12.456000+00:00"
        }
    }
