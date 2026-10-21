**To cancel a metadata model creation**

The following ``cancel-metadata-model-creation`` example cancels a metadata model creation operation. ::

    aws dms cancel-metadata-model-creation \
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

For more information, see `Creating statement metadata models <https://docs.aws.amazon.com/dms/latest/userguide/sc-metadata-model.html#sc-metadata-model-creation>`__ in the *AWS Database Migration Service User Guide*.
