**To create a RecordingConfiguration resource**

The following ``create-recording-configuration`` example creates RecordingConfiguration resource to enable recording to Amazon S3. ::

    aws ivs create-recording-configuration \
        --name test-recording-config \
        --destination-configuration 3={bucketName=demo-recording-bucket}

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
            "state": "CREATING",
            "tags": {}
        }
    }

For more information, see `Record to Amazon S3 <https://docs.aws.amazon.com/ivs/latest/userguide/record-to-S3.html>`__ in the *Amazon Interactive Video Service User Guide*.