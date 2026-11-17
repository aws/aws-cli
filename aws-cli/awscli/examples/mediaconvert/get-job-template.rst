**To get details for a job template**

The following ``get-job-template`` example displays the JSON definition of the specified custom job template. ::

    aws mediaconvert get-job-template \
        --name "DASH Streaming" \
        --endpoint-url https://abcd1234.mediaconvert.us-west-2.amazonaws.com

Output::

    {
        "JobTemplate": {
            "StatusUpdateInterval": "SECONDS_60",
            "LastUpdated": 1568652998,
            "Description": "Create a DASH streaming ABR stack",
            "CreatedAt": 1568652998,
            "Priority": 0,
            "Name": "DASH Streaming",
            "Settings": {
                "OutputGroups": [
                    {
                        "Name": "DASH ISO",
                        "OutputGroupSettings": {
                            "Type": "DASH_ISO_GROUP_SETTINGS",
                            "DashIsoGroupSettings": {
                                "FragmentLength": 2,
                                "SegmentControl": "SEGMENTED_FILES",
                                "SegmentLength": 30
                            }
                        },
                        "Outputs": [
                            {
                                "NameModifier": "_1080p",
                                "ContainerSettings": {
                                    "Container": "MPD"
                                },
                                "VideoDescription": {
                                    "Width": 1920,
                                    "Height": 1080,
                                    "CodecSettings": {
                                        "Codec": "H_264",
                                        "H264Settings": {
                                            "MaxBitrate": 6000000,
                                            "RateControlMode": "QVBR"
                                        }
                                    }
                                }
                            },
                            {
                                "NameModifier": "_720p",
                                "ContainerSettings": {
                                    "Container": "MPD"
                                },
                                "VideoDescription": {
                                    "Width": 1280,
                                    "Height": 720,
                                    "CodecSettings": {
                                        "Codec": "H_264",
                                        "H264Settings": {
                                            "MaxBitrate": 3500000,
                                            "RateControlMode": "QVBR"
                                        }
                                    }
                                }
                            },
                            {
                                "NameModifier": "_audio",
                                "ContainerSettings": {
                                    "Container": "MPD"
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
            "Arn": "arn:aws:mediaconvert:us-west-2:123456789012:jobTemplates/DASH Streaming",
            "Type": "CUSTOM"
        }
    }

For more information, see `Working with AWS Elemental MediaConvert Job Templates <https://docs.aws.amazon.com/mediaconvert/latest/ug/working-with-job-templates.html>`__ in the *AWS Elemental MediaConvert User Guide*.
