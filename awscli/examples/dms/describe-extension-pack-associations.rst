**To describe extension pack associations**

The following ``describe-extension-pack-associations`` example retrieves the status of operations that apply an extension pack to the target database, identified by their request IDs. ::

    aws dms describe-extension-pack-associations \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --filters Name=request-id,Values=a1b2c3d4-5678-90ab-cdef-EXAMPLE11111,a1b2c3d4-5678-90ab-cdef-EXAMPLE22222,a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

Output::

    {
        "Requests": [
            {
                "Status": "SUCCESS",
                "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "MigrationProjectArn": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS"
            },
            {
                "Status": "IN_PROGRESS",
                "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "MigrationProjectArn": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS",
                "Progress": {
                    "ProgressPercent": 50.0,
                    "ProgressStep": "IN_PROGRESS"
                }
            },
            {
                "Status": "FAILED",
                "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "MigrationProjectArn": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS",
                "Error": {
                    "defaultErrorDetails": {
                        "Message": "The database user in your target secret does not have sufficient privileges. Grant the required privileges and try again."
                    }
                }
            }
        ]
    }

For more information, see `Using extension packs <https://docs.aws.amazon.com/dms/latest/userguide/extension-pack.html>`__ in the *AWS Database Migration Service User Guide*.
