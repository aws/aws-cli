**To update a replication set**

The following ``update-replication-set`` example deletes the us-west-2 Region from the replication set. ::

    aws ssm-incidents update-replication-set \
        --arn "arn:aws:ssm-incidents::123456789012:replication-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --actions '[{"deleteRegionAction": {"regionName": "us-west-2"}}]'

This command produces no output.

For more information, see `Configuring replication sets and Findings in Incident Manager <https://docs.aws.amazon.com/incident-manager/latest/userguide/general-settings.html>`__ in the *Incident Manager User Guide*.