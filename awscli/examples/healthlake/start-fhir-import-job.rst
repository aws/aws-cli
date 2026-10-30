**To start a FHIR import job**

The following ``start-fhir-import-job`` example shows how to start a FHIR import job using AWS HealthLake. ::

    aws healthlake start-fhir-import-job \
        --input-data-config S3Uri="s3://amzn-s3-demo-bucket/healthlake/" \
        --job-output-data-config '{"S3Configuration": {"S3Uri":"s3://amzn-s3-demo-bucket/healthlake/","KmsKeyId":"arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"}}' \
        --datastore-id a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 \
        --data-access-role-arn "arn:aws:iam::123456789012:role/HealthLakeDataAccessRole"

Output::

    {
        "DatastoreId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        "JobStatus": "SUBMITTED",
        "JobId": "c145fbb27b192af392f8ce6e7838e34f"
    }

For more information, see `Importing files to a FHIR data store <https://docs.aws.amazon.com/healthlake/latest/devguide/import-datastore.html>`__ in the *AWS HealthLake Developer Guide*.

