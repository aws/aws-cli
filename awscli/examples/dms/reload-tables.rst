**To refresh the list of tables available at an endpoint**

The following ``reload-tables`` example reloads the list of available tables at an endpoint. ::

    aws dms reload-tables \
        --replication-task-arn "arn:aws:dms:us-west-2:123456789012:task:K55IUCGBASJS5VHZJIINA45FII" \
        --tables-to-reload "SchemaName=prodrep,TableName=ACCT_BAL"

Output::

    {
        "ReplicationTaskArn": "arn:aws:dms:us-west-2:123456789012:task:K55IUCGBASJS5VHZJIINA45FII"
    }

For more information, see `Reloading tables during a task <https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.ReloadTables.html>`__ in the *AWS Database Migration Service User Guide*.
