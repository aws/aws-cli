**To create a custom output preset**

The following ``create-preset`` example creates a custom output preset based on the output settings that are specified in the file ``preset.json``. You can specify the category, description, and name either in the JSON file or at the command line. ::

    aws mediaconvert create-preset \
        --endpoint-url https://abcd1234.mediaconvert.region-name-1.amazonaws.com \
        --cli-input-json file://~/preset.json

Contents of ``preset.json``::

    {
        "Name": "SimpleMP4",
        "Description": "MP4 output with H.264 video and AAC audio",
        "Settings": {
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
    }

If you create your preset JSON file by using ``get-preset`` and then modifying the output file, ensure that you remove the following key-value pairs: ``LastUpdated``, ``Arn``, ``Type``, and ``CreatedAt``.

To get your account-specific endpoint, use ``describe-endpoints``, or send the command without the endpoint. The service returns an error and your endpoint.

Output::

    {
        "Preset": {
            "Arn": "arn:aws:mediaconvert:region-name-1:123456789012:presets/SimpleMP4",
            "CreatedAt": "2024-04-01T17:22:05+00:00",
            "Description": "Creates basic MP4 file. No filtering or preprocessing.",
            "LastUpdated": "2024-04-01T17:22:05+00:00",
            "Name": "SimpleMP4",
            "Settings": {
                "ContainerSettings": {
                    "Container": "MP4",
                    "Mp4Settings": {
                        "CslgAtom": "INCLUDE",
                        "FreeSpaceBox": "EXCLUDE",
                        "MoovPlacement": "PROGRESSIVE_DOWNLOAD"
                    }
                },
                "VideoDescription": {
                    "CodecSettings": {
                        "Codec": "H_264",
                        "H264Settings": {
                            "Bitrate": 400000,
                            "CodecProfile": "MAIN",
                            "RateControlMode": "CBR"
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
            },
            "Type": "CUSTOM"
        }
    }

For more information, see `Working with output presets <https://docs.aws.amazon.com/mediaconvert/latest/ug/working-with-presets.html>`__ in the *AWS Elemental MediaConvert User Guide*.
