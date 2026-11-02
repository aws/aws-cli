**To start a FHIR export job**

The following ``start-fhir-export-job`` example shows how to start a FHIR export job using AWS HealthLake. ::

    aws healthlake start-fhir-export-job \
        --output-data-config '{"S3Configuration": {"S3Uri":"s3://amzn-s3-demo-bucket/healthlake/","KmsKeyId":"arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"}}' \
        --datastore-id a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 \
        --data-access-role-arn arn:aws:iam::123456789012:role/HealthLakeDataAccessRole

Output::

    {
        "DatastoreId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        "JobStatus": "SUBMITTED",
        "JobId": "9b9a51943afaedd0a8c0c26c49135a31"
    }

For more information, see `Exporting files from a FHIR data store <https://docs.aws.amazon.com/healthlake/latest/devguide/export-datastore.html>`__ in the *AWS HealthLake Developer Guide*.
