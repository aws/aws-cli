**To modify objects of governed table**

The following ``update-table-objects`` example adds provided S3 objects to the specified governed table. ::

    aws lakeformation update-table-objects \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "CatalogId": "123456789012",
        "DatabaseName": "tpc",
        "TableName": "dl_tpc_household_demographics_gov",
        "TransactionId": "12347a9f75424b9b915f6ff201d2a190",
        "WriteOperations": [{
            "AddObject": {
                "Uri": "s3://amzn-s3-demo-bucket/target/dl_tpc_household_demographics_gov/run-unnamed-1-part-block-0-r-00000-snappy-ff26b17504414fe88b302cd795eabd00.parquet",
                "ETag": "1234ab1fc50a316b149b4e1f21a73800",
                "Size": 42200
            }
        }]
    }

This command produces no output.
