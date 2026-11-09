**To schedule a pending maintenance action**

The following ``apply-pending-maintenance-action`` example schedules the pending operating system update for the specified Amazon DocumentDB elastic cluster to be applied during the next maintenance window. ::

    aws docdb-elastic apply-pending-maintenance-action \
        --resource-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --apply-action OS_UPDATE \
        --opt-in-type NEXT_MAINTENANCE

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

For more information, see `Maintaining Amazon DocumentDB elastic clusters <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-cluster-maintenance.html>`__ in the *Amazon DocumentDB Developer Guide*.
