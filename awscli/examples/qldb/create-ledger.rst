**Example 1: To create a ledger with default properties**

The following ``create-ledger`` example creates a ledger with the name ``myExampleLedger`` and the permissions mode ``ALLOW_ALL``. The optional parameter for deletion protection is not specified, so it defaults to ``true``. ::

    aws qldb create-ledger \
        --name myExampleLedger \
        --permissions-mode ALLOW_ALL

Output::

    {
        "State": "CREATING",
        "Arn": "arn:aws:qldb:us-west-2:123456789012:ledger/myExampleLedger",
        "DeletionProtection": true,
        "CreationDateTime": 1568839243.951,
        "Name": "myExampleLedger"
    }

**Example 2: To create a ledger with deletion protection disabled and with specified tags**

The following ``create-ledger`` example creates a ledger with the name ``myExampleLedger2`` and the permissions mode ``ALLOW_ALL``. The deletion protection feature is disabled, and the specified tags are attached to the resource. ::

    aws qldb create-ledger \
        --name myExampleLedger \
        --no-deletion-protection \
        --permissions-mode ALLOW_ALL \
        --tags IsTest=true,Domain=Test

Output::

    {
        "Arn": "arn:aws:qldb:us-west-2:123456789012:ledger/myExampleLedger2",
        "DeletionProtection": false,
        "CreationDateTime": 1568839543.557,
        "State": "CREATING",
        "Name": "myExampleLedger2"
    }


For more information, see `Basic Operations for Amazon QLDB Ledgers <https://docs.aws.amazon.com/qldb/latest/developerguide/ledger-management.basics.html>`__ in the *Amazon QLDB Developer Guide*.
