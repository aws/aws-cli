**To start a FHIR export job**

The following ``start-fhir-export-job`` example shows how to start a FHIR export job using Amazon HealthLake. ::

    aws healthlake start-fhir-export-job \
        --output-data-config '{"S3Configuration": {"S3Uri":"s3://outputS3Bucket/healthlake-output","KmsKeyId":"arn:aws:kms:us-east-1:012345678910:key/d330e7fc-b56c-4216-a250-f4c43ef46e83"}}' \
        --datastore-id (Datastore ID) \
        --data-access-role-arn arn:aws:iam::(AWS Account ID):role/(Role Name)

Output::

    {
        "DatastoreId": "(Datastore ID)",
        "JobStatus": "SUBMITTED",
        "JobId": "9b9a51943afaedd0a8c0c26c49135a31"
    }

For more information, see `Exporting files from a FHIR Data Store <https://docs.aws.amazon.com/healthlake/latest/devguide/export-datastore.html>`__ in the *Amazon HealthLake Developer Guide*.
