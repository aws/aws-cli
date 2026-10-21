**To cancel a metadata model conversion**

The following ``cancel-metadata-model-conversion`` example cancels a metadata model conversion operation. ::

    aws dms cancel-metadata-model-conversion \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --request-identifier a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Request": {
            "Status": "CANCELING",
            "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "MigrationProjectArn": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS"
        }
    }

For more information, see `Converting database schemas <https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion-convert.html>`__ in the *AWS Database Migration Service User Guide*.
