**To delete the replication set**

The following ``delete-replication-set`` example deletes the replication set from your Amazon Web Services account. Deleting the replication set also deletes all Incident Manager data. This can't be undone. ::

    aws ssm-incidents delete-replication-set \
        --arn "arn:aws:ssm-incidents::111122223333:replication-set/c4bcb603-4bf9-bb3f-413c-08df53673b57"

This command produces no output.

For more information, see `Configuring replication sets and Findings in Incident Manager <https://docs.aws.amazon.com/incident-manager/latest/userguide/general-settings.html>`__ in the *Incident Manager User Guide*.