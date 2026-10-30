**To describe a FHIR import job**

The following ``describe-fhir-import-job`` example shows how to learn the properties of a FHIR import job using AWS HealthLake. ::

    aws healthlake describe-fhir-import-job \
        --datastore-id a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 \
        --job-id c145fbb27b192af392f8ce6e7838e34f

Output::

    {
        "ImportJobProperties": {
        "InputDataConfig": {
            "S3Uri": "s3://amzn-s3-demo-bucket/healthlake/"
        },
        "DataAccessRoleArn": "arn:aws:iam::123456789012:role/HealthLakeDataAccessRole",
        "JobStatus": "COMPLETED",
        "JobId": "c145fbb27b192af392f8ce6e7838e34f",
        "SubmitTime": 1606272542.161,
        "EndTime": 1606272609.497,
        "DatastoreId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
        }
    }

For more information, see `Importing files to a FHIR data store <https://docs.aws.amazon.com/healthlake/latest/devguide/import-datastore.html>`__ in the *AWS HealthLake Developer Guide*.
