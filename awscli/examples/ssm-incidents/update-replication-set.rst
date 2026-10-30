**To update a replication set**

The following ``update-replication-set`` example deletes the us-east-2 Region from the replication set. ::

    aws ssm-incidents update-replication-set \
        --arn "arn:aws:ssm-incidents::111122223333:replication-set/a2bcc5c9-0f53-8047-7fef-c20749989b40" \
        --actions '[{"deleteRegionAction": {"regionName": "us-east-2"}}]'

This command produces no output.

For more information, see `Configuring replication sets and Findings in Incident Manager <https://docs.aws.amazon.com/incident-manager/latest/userguide/general-settings.html>`__ in the *Incident Manager User Guide*.