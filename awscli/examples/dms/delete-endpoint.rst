**To delete an endpoint**

The following ``delete-endpoint`` example deletes an endpoint. ::

    aws dms delete-endpoint \
        --endpoint-arn arn:aws:dms:us-west-2:123456789012:endpoint:OUJJVXO4XZ4CYTSEG5XGMN2R3Y

Output::

    {
        "Endpoint": {
            "EndpointIdentifier": "src-endpoint",
            "EndpointType": "SOURCE",
            "EngineName": "s3",
            "EngineDisplayName": "Amazon S3",
            "ExtraConnectionAttributes": "bucketFolder=sourcedata;bucketName=amzn-s3-demo-bucket;compressionType=NONE;csvDelimiter=,;csvRowDelimiter=\\n;",
            "Status": "deleting",
            "EndpointArn": "arn:aws:dms:us-west-2:123456789012:endpoint:OUJJVXO4XZ4CYTSEG5XGMN2R3Y",
            "SslMode": "none",
            "ServiceAccessRoleArn": "arn:aws:iam::123456789012:role/my-s3-access-role",
            "S3Settings": {
                "ServiceAccessRoleArn": "arn:aws:iam::123456789012:role/my-s3-access-role",
                "CsvRowDelimiter": "\\n",
                "CsvDelimiter": ",",
                "BucketFolder": "sourcedata",
                "BucketName": "amzn-s3-demo-bucket",
                "CompressionType": "NONE",
                "EnableStatistics": true
            }
        }
    }

For more information, see `Working with AWS DMS Endpoints <https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Endpoints.html>`__ in the *AWS Database Migration Service User Guide*.
