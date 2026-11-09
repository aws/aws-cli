**To list pending maintenance actions**

The following ``list-pending-maintenance-actions`` example lists the pending maintenance actions for the Amazon DocumentDB elastic clusters in your AWS account. ::

    aws docdb-elastic list-pending-maintenance-actions

Output::

    {
        "resourcePendingMaintenanceActions": [
            {
                "pendingMaintenanceActionDetails": [
                    {
                        "action": "OS_UPDATE",
                        "description": "New Operating System update is available"
                    }
                ],
                "resourceArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ]
    }

For more information, see `Viewing pending elastic cluster maintenance actions <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-cluster-maintenance.html#view-elastic-cluster-maintenance>`__ in the *Amazon DocumentDB Developer Guide*.
