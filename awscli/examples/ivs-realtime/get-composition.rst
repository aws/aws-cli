**To get a composition**

The following ``get-composition`` example gets the composition for the ARN (Amazon Resource Name) specified. ::

    aws ivs-realtime get-composition \
        --name arn "arn:aws:ivs:ap-northeast-1:123456789012:composition/abcdABCDefgh"

Output::

    {
        "composition": {
            "arn": "arn:aws:ivs:ap-northeast-1:123456789012:composition/abcdABCDefgh",
            "destinations": [
                {
                    "configuration": {
                        "channel": {
                            "channelArn": "arn:aws:ivs:ap-northeast-1:123456789012:channel/abcABCdefDEg",
                            "encoderConfigurationArn": "arn:aws:ivs:ap-northeast-1:123456789012:encoder-configuration/ABabCDcdEFef"
                        },
                        "name": ""
                    },
                    "id": "AabBCcdDEefF",
                    "startTime": "2023-10-16T23:26:00+00:00",
                    "state": "ACTIVE"
                },
                {
                    "configuration": {
                        "name": "",
                        "s3": {
                            "encoderConfigurationArns": [
                                "arn:aws:ivs:arn:aws:ivs:ap-northeast-1:123456789012:encoder-configuration/ABabCDcdEFef"
                            ],
                            "recordingConfiguration": {
                                "format": "HLS"
                            },
                            "storageConfigurationArn": "arn:arn:aws:ivs:ap-northeast-1:123456789012:storage-configuration/FefABabCDcdE"
                        }
                    },
                    "detail": {
                        "s3": {
                            "recordingPrefix": "aBcDeFgHhGfE/AbCdEfGhHgFe/GHFabcgefABC/composite"
                        }
                    },
                    "id": "GHFabcgefABC",
                    "startTime": "2023-10-16T23:26:00+00:00",
                    "state": "STARTING"
                }
            ],
            "layout": {
                "grid": {
                    "featuredParticipantAttribute": ""
                }
            },
            "stageArn": "arn:aws:ivs:ap-northeast-1:123456789012:stage/defgABCDabcd",
            "startTime": "2023-10-16T23:24:00+00:00",
            "state": "ACTIVE",
            "tags": {}
        }
    }

For more information, see `Enabling Multiple Hosts on an Amazon IVS Stream <https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/multiple-hosts.html>`__ in the *Amazon Interactive Video Service User Guide*.