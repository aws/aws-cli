**To describe metadata model exports to target**

The following ``describe-metadata-model-exports-to-target`` example retrieves the status of operations that export converted metadata models to the target database, identified by their request IDs. ::

    aws dms describe-metadata-model-exports-to-target \
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
                    "TotalObjects": 100,
                    "ProgressStep": "APPLYING",
                    "ProcessedObject": {
                        "EndpointType": "TARGET"
                    }
                }
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

For more information, see `Applying your converted code <https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion-save-apply.html#schema-conversion-apply>`__ in the *AWS Database Migration Service User Guide*.
