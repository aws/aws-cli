**To create a job template**

The following ``create-job-template`` example creates a job template with the transcoding settings that are specified in the file ``job-template.json`` that resides on your system. ::

    aws mediaconvert create-job-template \
        --endpoint-url https://abcd1234.mediaconvert.region-name-1.amazonaws.com \
        --name JobTemplate1 \
        --cli-input-json file://~/job-template.json

Contents of ``job-template.json``::

    {
        "Description": "Job template that creates an MP4 output with H.264 video and AAC audio",
        "Settings": {
            "TimecodeConfig": {
                "Source": "ZEROBASED"
            },
            "Inputs": [
                {
                    "AudioSelectors": {
                        "Audio Selector 1": {
                            "DefaultSelection": "DEFAULT"
                        }
                    },
                    "VideoSelector": {},
                    "TimecodeSource": "ZEROBASED"
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
                                "Container": "MP4"
                            },
                            "VideoDescription": {
                                "CodecSettings": {
                                    "Codec": "H_264",
                                    "H264Settings": {
                                        "RateControlMode": "QVBR",
                                        "MaxBitrate": 5000000,
                                        "SceneChangeDetect": "TRANSITION_DETECTION",
                                        "QualityTuningLevel": "SINGLE_PASS"
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
        }
    }

If you create your job template JSON file by using ``get-job-template`` and then modifying the file, remove the ``JobTemplate`` object, but keep the `Settings` child object inside it. Also, make sure to remove the following key-value pairs: ``LastUpdated``, ``Arn``, ``Type``, and ``CreatedAt``. You can specific the category, description, name, and queue either in the JSON file or at the command line.

To get your account-specific endpoint, use ``describe-endpoints``, or send the command without the endpoint. The service returns an error and your endpoint.

If your request is successful, the service returns the JSON specification for the job template that you created.

Output::

    {
        "JobTemplate": {
            "Arn": "arn:aws:mediaconvert:region-name-1:123456789012:jobTemplates/JobTemplate1",
            "CreatedAt": "2024-04-01T17:20:31+00:00",
            "LastUpdated": "2024-04-01T17:20:31+00:00",
            "Name": "JobTemplate1",
            "Priority": 0,
            "Settings": {
                "OutputGroups": [
                    {
                        "Name": "File Group",
                        "OutputGroupSettings": {
                            "Type": "FILE_GROUP_SETTINGS",
                            "FileGroupSettings": {}
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
            "StatusUpdateInterval": "SECONDS_60",
            "Type": "CUSTOM"
        }
    }

For more information, see `Working with job templates <https://docs.aws.amazon.com/mediaconvert/latest/ug/working-with-job-templates.html>`__ in the *AWS Elemental MediaConvert User Guide*.
