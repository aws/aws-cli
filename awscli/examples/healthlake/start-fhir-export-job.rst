**To start a FHIR export job**

The following ``start-fhir-export-job`` example shows how to start a FHIR export job using AWS HealthLake. ::

    aws healthlake start-fhir-export-job \
        --output-data-config '{"S3Configuration": {"S3Uri":"s3://(Bucket Name)/(Prefix Name)/","KmsKeyId":"arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"}}' \
        --datastore-id (Data store ID) \
        --data-access-role-arn arn:aws:iam::(AWS Account ID):role/(Role Name)

Output::

    {
        "DatastoreId": "(Data store ID)",
        "JobStatus": "SUBMITTED",
        "JobId": "9b9a51943afaedd0a8c0c26c49135a31"
    }

For more information, see `Exporting files from a FHIR data store <https://docs.aws.amazon.com/healthlake/latest/devguide/export-datastore.html>`__ in the *AWS HealthLake Developer Guide*.
