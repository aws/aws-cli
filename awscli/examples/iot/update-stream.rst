**To update a stream**

The following ``update-stream`` example updates an existing stream. The stream version is incremented by one. ::

    aws iot update-stream \
        --cli-input-json file://update-stream.json

Contents of ``update-stream.json``::

    {
        "streamId": "stream12345",
        "description": "This stream is used for Amazon FreeRTOS OTA Update 12345.",
        "files": [
            {
                "fileId": 123,
                "s3Location": {
                    "bucket":"codesign-ota-bucket",
                    "key":"a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                }
            }
        ]
        "roleArn": "arn:aws:iam:us-west-2:123456789012:role/service-role/my_ota_stream_role"
    }

Output::

    {
        "streamId": "stream12345",
        "streamArn": "arn:aws:iot:us-west-2:123456789012:stream/stream12345",
        "description": "This stream is used for Amazon FreeRTOS OTA Update 12345.",
        "streamVersion": 2
    }

For more information, see `MQTT-based file delivery <https://docs.aws.amazon.com/iot/latest/developerguide/mqtt-based-file-delivery.html>`__ in the *AWS IoT Core Developer Guide*.
