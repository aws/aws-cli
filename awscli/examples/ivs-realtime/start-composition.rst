**To start a composition**

The following ``start-composition`` example starts a composition for the specified stage to be streamed to the specified locations. ::

    aws ivs-realtime start-composition \
        --stage-arn arn:aws:ivs:ap-northeast-1:123456789012:stage/defgABCDabcd \
        --destinations '[{"channel": {"channelArn": "arn:aws:ivs:ap-northeast-1:123456789012:channel/abcABCdefDEg", \
            "encoderConfigurationArn": "arn:aws:ivs:ap-northeast-1:123456789012:encoder-configuration/ABabCDcdEFef"}}, \
            {"s3":{"encoderConfigurationArns":["arn:aws:ivs:ap-northeast-1:123456789012:encoder-configuration/ABabCDcdEFef"], \ 
            "storageConfigurationArn":"arn:aws:ivs:ap-northeast-1:123456789012:storage-configuration/FefABabCDcdE"}}]'

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
                    "state": "STARTING"
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
            "state": "STARTING",
            "tags": {}
        }
    }

For more information, see `Enabling Multiple Hosts on an Amazon IVS Stream <https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/multiple-hosts.html>`__ in the *Amazon Interactive Video Service User Guide*.