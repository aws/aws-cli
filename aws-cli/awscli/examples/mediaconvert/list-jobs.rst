**To get details for all jobs in a region**

The following ``list-jobs`` example requests the information for all of your jobs in the specified region. ::

    aws mediaconvert list-jobs \
        --endpoint-url https://abcd1234.mediaconvert.region-name-1.amazonaws.com

To get your account-specific endpoint, use ``describe-endpoints``, or send the command without the endpoint. The service returns an error and your endpoint.

Output::

    {
        "Jobs": [
            {
                "AccelerationStatus": "NOT_APPLICABLE",
                "Arn": "arn:aws:mediaconvert:region-name-1:123456789012:jobs/1234567891234-abc123",
                "CreatedAt": "2024-04-01T17:35:12+00:00",
                "Id": "1234567891234-abc123",
                "Priority": 0,
                "Queue": "arn:aws:mediaconvert:region-name-1:123456789012:queues/Default",
                "Role": "arn:aws:iam::123456789012:role/MediaConvertServiceRole",
                "Settings": {
                    "Inputs": [
                        {
                            "FileInput": "s3://amzn-s3-demo-bucket/input/file-name.mp4"
                        }
                    ],
                    "OutputGroups": [
                        {
                            "Name": "File Group",
                            "OutputGroupSettings": {
                                "Type": "FILE_GROUP_SETTINGS",
                                "FileGroupSettings": {
                                    "Destination": "s3://amzn-s3-demo-bucket/output/"
                                }
                            },
                            "Outputs": [
                                {
                                    "ContainerSettings": {
                                        "Container": "MP4",
                                        "Mp4Settings": {
                                            "CslgAtom": "INCLUDE",
                                            "FreeSpaceBox": "EXCLUDE",
                                            "MoovPlacement": "PROGRESSIVE_DOWNLOAD"
                                        }
                                    },
                                    "VideoDescription": {
                                        "Width": 1920,
                                        "Height": 1080,
                                        "CodecSettings": {
                                            "Codec": "H_264",
                                            "H264Settings": {
                                                "MaxBitrate": 10000000,
                                                "RateControlMode": "QVBR"
                                            }
                                        }
                                    },
                                    "AudioDescriptions": [
                                        {
                                            "CodecSettings": {
                                                "Codec": "AAC",
                                                "AacSettings": {
                                                    "Bitrate": 96000,
                                                    "CodingMode": "CODING_MODE_2_0",
                                                    "SampleRate": 48000
                                                }
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "Status": "PROGRESSING",
                "StatusUpdateInterval": "SECONDS_60",
                "Timing": {
                    "StartTime": "2024-04-01T17:35:14+00:00",
                    "SubmitTime": "2024-04-01T17:35:12+00:00"
                },
                "UserMetadata": {},
                "CurrentPhase": "TRANSCODING",
                "JobPercentComplete": 45
            },
            {
                "AccelerationStatus": "NOT_APPLICABLE",
                "Arn": "arn:aws:mediaconvert:region-name-1:123456789012:jobs/1234567890987-1ab2c3",
                "CreatedAt": "2024-04-01T16:20:01+00:00",
                "Id": "1234567890987-1ab2c3",
                "Priority": 0,
                "Queue": "arn:aws:mediaconvert:region-name-1:123456789012:queues/Default",
                "Role": "arn:aws:iam::123456789012:role/MediaConvertServiceRole",
                "Settings": {
                    "Inputs": [
                        {
                            "FileInput": "s3://amzn-s3-demo-bucket/input/file-name.mp4"
                        }
                    ],
                    "OutputGroups": [
                        {
                            "Name": "File Group",
                            "OutputGroupSettings": {
                                "Type": "FILE_GROUP_SETTINGS",
                                "FileGroupSettings": {
                                    "Destination": "s3://amzn-s3-demo-bucket/output/"
                                }
                            },
                            "Outputs": [
                                {
                                    "ContainerSettings": {
                                        "Container": "MP4",
                                        "Mp4Settings": {
                                            "CslgAtom": "INCLUDE",
                                            "FreeSpaceBox": "EXCLUDE",
                                            "MoovPlacement": "PROGRESSIVE_DOWNLOAD"
                                        }
                                    },
                                    "VideoDescription": {
                                        "Width": 1920,
                                        "Height": 1080,
                                        "CodecSettings": {
                                            "Codec": "H_264",
                                            "H264Settings": {
                                                "MaxBitrate": 10000000,
                                                "RateControlMode": "QVBR"
                                            }
                                        }
                                    },
                                    "AudioDescriptions": [
                                        {
                                            "CodecSettings": {
                                                "Codec": "AAC",
                                                "AacSettings": {
                                                    "Bitrate": 96000,
                                                    "CodingMode": "CODING_MODE_2_0",
                                                    "SampleRate": 48000
                                                }
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "Status": "COMPLETE",
                "StatusUpdateInterval": "SECONDS_60",
                "Timing": {
                    "FinishTime": "2024-04-01T16:22:48+00:00",
                    "StartTime": "2024-04-01T16:20:03+00:00",
                    "SubmitTime": "2024-04-01T16:20:01+00:00"
                },
                "UserMetadata": {}
            }
        ]
    }

For more information, see `Working with jobs <https://docs.aws.amazon.com/mediaconvert/latest/ug/working-with-jobs.html>`__ in the *AWS Elemental MediaConvert User Guide*.
