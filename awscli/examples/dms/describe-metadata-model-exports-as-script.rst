**To describe metadata model exports as script**

The following ``describe-metadata-model-exports-as-script`` example retrieves the status of operations that export metadata models as data definition language (DDL) scripts, identified by their request IDs. ::

    aws dms describe-metadata-model-exports-as-script \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --filters Name=request-id,Values=a1b2c3d4-5678-90ab-cdef-EXAMPLE11111,a1b2c3d4-5678-90ab-cdef-EXAMPLE22222,a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

Output::

    {
        "Requests": [
            {
                "Status": "SUCCESS",
                "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "MigrationProjectArn": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS",
                "ExportSqlDetails": {
                    "S3ObjectKey": "s3://amzn-s3-demo-bucket/example-migration-project/ExampleScript.zip",
                    "ObjectURL": "https://amzn-s3-demo-bucket.s3.us-east-1.amazonaws.com/example-migration-project/ExampleScript.zip"
                }
            },
            {
                "Status": "IN_PROGRESS",
                "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "MigrationProjectArn": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS",
                "Progress": {
                    "ProgressPercent": 50.0,
                    "TotalObjects": 100,
                    "ProgressStep": "IN_PROGRESS",
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

For more information, see `Saving your converted code to a SQL file <https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion-save-apply.html#schema-conversion-save>`__ in the *AWS Database Migration Service User Guide*.
