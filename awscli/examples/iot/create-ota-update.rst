**To create an OTA update for use with Amazon FreeRTOS**

The following ``create-ota-update`` example creates an AWS IoT OTAUpdate on a target group of things or groups. This is part of an Amazon FreeRTOS over-the-air update which makes it possible for you to deploy new firmware images to a single device or a group of devices. ::

    aws iot create-ota-update \
        --cli-input-json file://create-ota-update.json

Contents of ``create-ota-update.json``::

    {
        "otaUpdateId": "ota12345",
        "description": "A critical update needed right away.",
        "targets": [
            "device1",
            "device2",
            "device3",
            "device4"
        ],
        "targetSelection": "SNAPSHOT",
        "awsJobExecutionsRolloutConfig": {
            "maximumPerMinute": 10
        },
        "files": [
            {
              "fileName": "firmware.bin",
              "fileLocation": {
                "stream": {
                  "streamId": "004",
                  "fileId":123
                }
              },
              "codeSigning": {
                "awsSignerJobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
              }
            }
        ]
        "roleArn": "arn:aws:iam:123456789012:role/service-role/my_ota_role"
    }

Output::

    {
        "otaUpdateId": "ota12345",
        "awsIotJobId": "job54321",
        "otaUpdateArn": "arn:aws:iot:us-west-2:123456789012:otaupdate/itsaupdate",
        "awsIotJobArn": "arn:aws:iot:us-west-2:123456789012:job/itsajob",
        "otaUpdateStatus": "CREATE_IN_PROGRESS"
    }

For more information, see `Creating an OTA update with the AWS CLI <https://docs.aws.amazon.com/freertos/latest/userguide/ota-cli-workflow.html>`__ in the *FreeRTOS User Guide*.
