**To get the pending maintenance actions for an elastic cluster**

The following ``get-pending-maintenance-action`` example displays the pending maintenance actions for the specified Amazon DocumentDB elastic cluster. ::

    aws docdb-elastic get-pending-maintenance-action \
        --resource-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "resourcePendingMaintenanceAction": {
            "pendingMaintenanceActionDetails": [
                {
                    "action": "OS_UPDATE",
                    "description": "New Operating System update is available"
                }
            ],
            "resourceArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        }
    }

For more information, see `Viewing pending elastic cluster maintenance actions <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-cluster-maintenance.html#view-elastic-cluster-maintenance>`__ in the *Amazon DocumentDB Developer Guide*.
