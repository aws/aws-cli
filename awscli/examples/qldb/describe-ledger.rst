**To describe a ledger**

The following ``describe-ledger`` example displays the details for the specified ledger. ::

    aws qldb describe-ledger \
        --name myExampleLedger

Output::

    {
        "CreationDateTime": 1568839243.951,
        "Arn": "arn:aws:qldb:us-west-2:123456789012:ledger/myExampleLedger",
        "State": "ACTIVE",
        "Name": "myExampleLedger",
        "DeletionProtection": true
    }

For more information, see `Basic Operations for Amazon QLDB Ledgers <https://docs.aws.amazon.com/qldb/latest/developerguide/ledger-management.basics.html>`__ in the *Amazon QLDB Developer Guide*.
