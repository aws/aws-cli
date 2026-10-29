**To delete the replication set**

The following ``delete-replication-set`` example deletes the replication set from your Amazon Web Services account. Deleting the replication set also deletes all Incident Manager data. This can't be undone. ::

    aws ssm-incidents delete-replication-set \
        --arn "arn:aws:ssm-incidents::123456789012:replication-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Configuring replication sets and Findings in Incident Manager <https://docs.aws.amazon.com/incident-manager/latest/userguide/general-settings.html>`__ in the *Incident Manager User Guide*.