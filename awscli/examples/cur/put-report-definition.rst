
**To create an AWS Cost and Usage Reports**

This example creates a daily AWS Cost and Usage Report that can be uploaded into Amazon Redshift or Amazon QuickSight.

Command::

  aws cur --region us-east-1 put-report-definition --report-definition file://report-definition.json

report-definition.json::
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
     "S3Region": "us-east-1",
     "AdditionalArtifacts": [ 
        "REDSHIFT",
        "QUICKSIGHT"
     ]
   }
