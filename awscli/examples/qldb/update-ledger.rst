**To update properties of a ledger**

The following ``update-ledger`` example  updates the specified ledger to disable the deletion protection feature. ::

    aws qldb update-ledger \
        --name myExampleLedger \
        --no-deletion-protection

Output::

    {
        "CreationDateTime": 1568839243.951,
        "Arn": "arn:aws:qldb:us-west-2:123456789012:ledger/myExampleLedger",
        "DeletionProtection": false,
        "Name": "myExampleLedger",
        "State": "ACTIVE"
    }

For more information, see `Basic Operations for Amazon QLDB Ledgers <https://docs.aws.amazon.com/qldb/latest/developerguide/ledger-management.basics.html>`__ in the *Amazon QLDB Developer Guide*.
