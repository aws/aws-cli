**To export a conversion assessment report**

The following ``export-metadata-model-assessment`` example exports a conversion assessment report for all objects in the ``ExampleSchema`` schema. ::

    aws dms export-metadata-model-assessment \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --selection-rules '{"rules": [{"rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": {"server-name": "example-source-server.us-east-1.rds.amazonaws.com", "schema-name": "ExampleSchema"}, "rule-action": "explicit"}]}' \
        --file-name example-assessment-report \
        --assessment-report-types pdf csv

Output::

    {
        "PdfReport": {
            "S3ObjectKey": "example-migration-project/example-assessment-report.pdf",
            "ObjectURL": "https://amzn-s3-demo-bucket.s3.amazonaws.com/example-migration-project/example-assessment-report.pdf"
        },
        "CsvReport": {
            "S3ObjectKey": "example-migration-project/example-assessment-report.zip",
            "ObjectURL": "https://amzn-s3-demo-bucket.s3.amazonaws.com/example-migration-project/example-assessment-report.zip"
        }
    }

For more information, see `Creating database migration assessment reports <https://docs.aws.amazon.com/dms/latest/userguide/assessment-reports.html>`__ in the *AWS Database Migration Service User Guide*.
