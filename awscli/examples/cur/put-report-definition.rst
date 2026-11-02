**To create an AWS Cost and Usage Reports**

The following ``put-report-definition`` example creates a daily AWS Cost and Usage Report that you can upload into Amazon Redshift or Amazon QuickSight. ::

    aws cur put-report-definition \
        --report-definition file://report-definition.json

Contents of ``report-definition.json``::

    {
        "ReportName": "ExampleReport",
        "TimeUnit": "DAILY",
        "Format": "textORcsv",
        "Compression": "ZIP",
        "AdditionalSchemaElements": [ 
            "RESOURCES"
        ],
        "S3Bucket": "example-s3-bucket",
        "S3Prefix": "exampleprefix",
        "S3Region": "us-west-2",
        "AdditionalArtifacts": [ 
            "REDSHIFT",
            "QUICKSIGHT"
        ]
    }

This command produces no output.

For more information, see `Creating a Legacy CUR export <https://docs.aws.amazon.com/cur/latest/userguide/dataexports-create-legacy.html>`__ in the *AWS Data Exports User Guide*.

