**To change a preset**

The following ``update-preset`` example replaces the description for the specified preset. ::

    aws mediaconvert update-preset \
        --name Customer1 \
        --description "New description text." \
        --endpoint-url https://abcd1234.mediaconvert.us-west-2.amazonaws.com

Output::

    {
        "Preset": {
            "Arn": "arn:aws:mediaconvert:us-west-2:123456789012:presets/SimpleMP4",
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
            "Type": "CUSTOM",
            "LastUpdated": 1568938411,
            "Description": "New description text.",
            "Name": "SimpleMP4",
            "CreatedAt": 1568938240
        }
    }

For more information, see `Working with AWS Elemental MediaConvert Output Presets <https://docs.aws.amazon.com/mediaconvert/latest/ug/working-with-presets.html>`__ in the *AWS Elemental MediaConvert User Guide*.
