**To list all FHIR export jobs**

The following ``list-fhir-export-jobs`` example shows how to use the command to view a list of export jobs associated with an account. ::

    aws healthlake list-fhir-export-jobs \
        --datastore-id a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 \
        --submitted-before 2024-10-13T19:00:00Z \
        --submitted-after 2020-10-13T19:00:00Z \
        --job-name "FHIR-EXPORT" \
        --job-status SUBMITTED \
        --max-results 50

Output::

    {
        "ExportJobPropertiesList": [
            {
                "OutputDataConfig": {
                    "S3Configuration": {
                        "S3Uri": "s3://amzn-s3-demo-bucket/healthlake/",
                        "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                    }
                },
                "DataAccessRoleArn": "arn:aws:iam::123456789012:role/HealthLakeDataAccessRole",
                "JobStatus": "COMPLETED",
                "JobId": "c145fbb27b192af392f8ce6e7838e34f",
                "JobName": "FHIR-EXPORT",
                "SubmitTime": "2024-11-20T11:31:46.672000-05:00",
                "EndTime": "2024-11-20T11:34:01.636000-05:00",
                "DatastoreId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
            }
        ]
    }

For more information, see `Listing FHIR export jobs <https://docs.aws.amazon.com/healthlake/latest/devguide/exporting-fhir-data-list.html>`__ in the *AWS HealthLake Developer Guide*.
