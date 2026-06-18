**To describe metadata model creations**

The following ``describe-metadata-model-creations`` example retrieves the status of metadata model creation operations identified by their request IDs. ::

    aws dms describe-metadata-model-creations \
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
                "MigrationProjectArn": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS"
            },
            {
                "Status": "FAILED",
                "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "MigrationProjectArn": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS",
                "Error": {
                    "defaultErrorDetails": {
                        "Message": "No objects were found according to the specified selection rules. Please review your selection rules and try again."
                    }
                }
            }
        ]
    }

For more information, see `Creating statement metadata models <https://docs.aws.amazon.com/dms/latest/userguide/sc-metadata-model.html#sc-metadata-model-creation>`__ in the *AWS Database Migration Service User Guide*.
