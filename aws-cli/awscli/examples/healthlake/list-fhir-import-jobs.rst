**To list all FHIR import jobs**

The following ``list-fhir-import-jobs`` example shows how to use the command to view a list of all import jobs associated with an account. ::

    aws healthlake list-fhir-import-jobs \
        --datastore-id a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 \
        --submitted-before 2024-10-13T19:00:00Z \
        --submitted-after 2020-10-13T19:00:00Z \
        --job-name "FHIR-IMPORT" \
        --job-status SUBMITTED \
        --max-results 50

Output::

    {
        "ImportJobPropertiesList": [
            {
                "JobId": "c0fddbf76f238297632d4aebdbfc9ddf",
                "JobStatus": "COMPLETED",
                "SubmitTime": "2024-11-20T10:08:46.813000-05:00",
                "EndTime": "2024-11-20T10:10:09.093000-05:00",
                "DatastoreId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
                "InputDataConfig": {
                    "S3Uri": "s3://amzn-s3-demo-bucket/healthlake/"
                },
                "JobOutputDataConfig": {
                    "S3Configuration": {
                        "S3Uri": "s3://amzn-s3-demo-bucket/import/6407b9ae4c2def3cb6f1a46a0c599ec0-FHIR_IMPORT-c0fddbf76f238297632d4aebdbfc9ddf/",
                        "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                    }
                },
                "JobProgressReport": {
                    "TotalNumberOfScannedFiles": 1,
                    "TotalSizeOfScannedFilesInMB": 0.001798,
                    "TotalNumberOfImportedFiles": 1,
                    "TotalNumberOfResourcesScanned": 1,
                    "TotalNumberOfResourcesImported": 1,
                    "TotalNumberOfResourcesWithCustomerError": 0,
                    "TotalNumberOfFilesReadWithCustomerError": 0,
                    "Throughput": 0.0
                },
                "DataAccessRoleArn": "arn:aws:iam::123456789012:role/HealthLakeDataAccessRole"
            }
        ]
    }

For more information, see `Listing FHIR import jobs <https://docs.aws.amazon.com/healthlake/latest/devguide/importing-fhir-data-list.html>`__ in the *AWS HealthLake Developer Guide*.

