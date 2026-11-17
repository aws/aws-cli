**To retrieve a list of AWS Cost and Usage Reports**

The following ``describe-report-definitions`` example describes a list of AWS Cost and Usage Reports owned by an account. ::

    aws cur describe-report-definitions \
        --region us-east-1 \
        --max-items 5

Output::

    {
        "ReportDefinitions": [
            {
                "ReportName": "ExampleReport",
                "Compression": "ZIP",
                "S3Region": "us-east-1",
                "Format": "textORcsv",
                "S3Prefix": "exampleprefix",
                "S3Bucket": "example-s3-bucket",
                "TimeUnit": "DAILY",
                "AdditionalArtifacts": [
                    "REDSHIFT",
                    "QUICKSIGHT"
                ],
                "AdditionalSchemaElements": [
                    "RESOURCES"
                ]
            }
        ]
    }

For more information, see `What are AWS Cost and Usage Reports? <https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html>`__ in the *AWS Data Exports User Guide*.
