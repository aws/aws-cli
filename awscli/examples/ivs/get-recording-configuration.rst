**To get information about a RecordingConfiguration resource**

The following ``get-recording-configuration`` example gets information about the RecordingConfiguration resource for the specified ARN. ::

    aws ivs get-recording-configuration \
        --arn "arn:aws:ivs:us-west-2:123456789012:recording-configuration/ABcdef34ghIJ"

Output::

    {
        "recordingConfiguration": {
            "arn": "arn:aws:ivs:us-west-2:123456789012:recording-configuration/ABcdef34ghIJ",
            "name": "test-recording-config",
            "destinationConfiguration": {
                "s3": {
                    "bucketName": "demo-recording-bucket"
                }
            },
            "state": "ACTIVE",
            "tags": {}
        }
    }

For more information, see `Record to Amazon S3 <https://docs.aws.amazon.com/ivs/latest/userguide/record-to-S3.html>`__ in the *Amazon Interactive Video Service User Guide*.