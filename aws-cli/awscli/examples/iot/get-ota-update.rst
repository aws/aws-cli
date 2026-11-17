**To retrieve information about an OTA Update**

The following ``get-ota-update`` example displays details about the specified OTA Update. ::

    aws iot get-ota-update \
        --ota-update-id ota12345

Output::

    {
        "otaUpdateInfo": {
            "otaUpdateId": "ota12345",
            "otaUpdateArn": "arn:aws:iot:us-west-2:123456789012:otaupdate/itsaupdate",
            "creationDate": "2019-05-14T19:46:55.995000+00:00",
            "lastModifiedDate": "2019-05-14T19:46:55.995000+00:00",
            "description": "A critical update needed right away.",
            "targets": [
                "device1",
                "device2",
                "device3",
                "device4"
            ],
            "targetSelection": "SNAPSHOT",
            "protocols": ["HTTP"],
            "awsJobExecutionsRolloutConfig": {
                "maximumPerMinute": 10
            },
            "otaUpdateFiles": [
                {
                    "fileName": "firmware.bin",
                    "fileLocation": {
                        "stream": {
                            "streamId": "004",
                            "fileId": 123
                        }
                    },
                    "codeSigning": {
                        "awsSignerJobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                    }
                }
            ],
            "otaUpdateStatus": "CREATE_COMPLETE",
            "awsIotJobId": "job54321",
            "awsIotJobArn": "arn:aws:iot:us-west-2:123456789012:job/job54321",
            "errorInfo": {
            }
        }
    }

For more information, see `FreeRTOS Over-the-Air Updates <https://docs.aws.amazon.com/freertos/latest/userguide/freertos-ota-dev.html>`__ in the *FreeRTOS User Guide*.
