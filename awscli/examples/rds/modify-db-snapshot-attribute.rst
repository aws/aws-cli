**Example 1: To enable two AWS accounts to restore a DB snapshot**

The following ``modify-db-snapshot-attribute`` example grants permission to two AWS accounts, with the identifiers ``123456789111`` and ``123456789222``, to restore the DB snapshot named ``mydbsnapshot``. ::

    aws rds modify-db-snapshot-attribute \
        --db-snapshot-identifier mydbsnapshot \
        --attribute-name restore \
        --values-to-add {"123456789111","123456789222"}

Output::

    {
        "DBSnapshotAttributesResult": {
            "DBSnapshotIdentifier": "mydbsnapshot",
            "DBSnapshotAttributes": [
                {
                    "AttributeName": "restore",
                    "AttributeValues": [
                        "123456789111",
                        "123456789222"
                    ]
                }
            ]
        }
    }

For more information, see `Sharing a Snapshot <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html#USER_ShareSnapshot.Sharing>`__ in the *Amazon RDS User Guide*.

**Example 2: To prevent an AWS account from restoring a DB snapshot**

The following ``modify-db-snapshot-attribute`` example removes permission from a particular AWS account to restore the DB snapshot named ``mydbsnapshot``. When specifying a single account, the account identifier can't be surrounded by quotations marks or braces. ::

    aws rds modify-db-snapshot-attribute \
        --db-snapshot-identifier mydbsnapshot \
        --attribute-name restore \
        --values-to-remove 123456789222

Output::

    {
        "DBSnapshotAttributesResult": {
            "DBSnapshotIdentifier": "mydbsnapshot",
            "DBSnapshotAttributes": [
                {
                    "AttributeName": "restore",
                    "AttributeValues": [
                        "123456789111"
                    ]
                }
            ]
        }
    }

For more information, see `Sharing a Snapshot <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html#USER_ShareSnapshot.Sharing>`__ in the *Amazon RDS User Guide*.