**To list objects of governed table**

The following ``get-table-objects`` example returns the set of Amazon S3 objects that make up the specified governed table. ::

    aws lakeformation get-table-objects \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "CatalogId": "123456789012",
        "DatabaseName": "tpc",
        "TableName": "dl_tpc_household_demographics_gov",
        "QueryAsOfTime": "2022-08-10T15:00:00"
    }

Output::

    {
        "Objects": [{
            "PartitionValues": [],
            "Objects": [{
                "Uri": "s3://amzn-s3-demo-bucket/target/dl_tpc_household_demographics_gov/run-unnamed-1-part-block-0-r-00000-snappy-ff26b17504414fe88b302cd795eabd00.parquet",
                "ETag": "12345b1fc50a316b149b4e1f21a73800",
                "Size": 43235
            }]
        }]
    }
