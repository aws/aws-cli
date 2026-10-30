**To get information about a stream**

The following ``describe-stream`` example displays the details about the specified stream. ::

    aws iot describe-stream \
        --stream-id stream12345

Output::

    {
        "streamInfo": {
            "streamId": "stream12345",
            "streamArn": "arn:aws:iot:us-west-2:123456789012:stream/stream12345",
            "streamVersion": 1,
            "description": "This stream is used for Amazon FreeRTOS OTA Update 12345.",
            "files": [
                {
                    "fileId": 123,
                    "s3Location": {
                        "bucket":"codesign-ota-bucket",
                        "key":"a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                    }
                }
            ],
            "createdAt": 1557863215.995,
            "lastUpdatedAt": 1557863215.995,
            "roleArn": "arn:aws:iam:123456789012:role/service-role/my_ota_stream_role"
        }
    }

For more information, see `MQTT-based file delivery <https://docs.aws.amazon.com/iot/latest/developerguide/mqtt-based-file-delivery.html>`__ in the *AWS IoT Core Developer Guide*.
