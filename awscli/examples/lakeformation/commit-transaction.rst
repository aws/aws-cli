**To commit transaction**

The following ``commit-transaction`` example commits the transaction. ::

    aws lakeformation commit-transaction \
        --transaction-id='b014d972ca8347b89825e33c5774aec4'

Output::

    {
        "TransactionStatus": "committed"
    }
