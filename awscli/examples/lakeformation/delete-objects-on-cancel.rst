**To delete object when transaction is cancelled**

The following ``delete-objects-on-cancel`` example deletes the listed s3 object when the transaction is cancelled. ::

    aws lakeformation delete-objects-on-cancel \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "CatalogId": "123456789012",
        "DatabaseName": "tpc",
        "TableName": "dl_tpc_household_demographics_gov",
        "TransactionId": "1234d972ca8347b89825e33c5774aec4",
        "Objects": [{
            "Uri": "s3://amzn-s3-demo-bucket/target/dl_tpc_household_demographics_gov/run-unnamed-1-part-block-0-r-00000-snappy-ff26b17504414fe88b302cd795eabd00.parquet",
            "ETag": "1234ab1fc50a316b149b4e1f21a73800"
        }]
    }

This command produces no output.
