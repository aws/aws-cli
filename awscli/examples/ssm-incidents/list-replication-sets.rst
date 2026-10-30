**To list the replication set**

The following ``list-replication-sets`` example lists the replication set Incident Manager uses to replicate and encrypt data in your AWS account. ::

    aws ssm-incidents list-replication-sets 

Output::

    {
        "replicationSetArns": [
            "arn:aws:ssm-incidents::123456789012:replication-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        ]
    }

For more information, see `Configuring replication sets and Findings in Incident Manager <https://docs.aws.amazon.com/incident-manager/latest/userguide/general-settings.html>`__ in the *Incident Manager User Guide*.