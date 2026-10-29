**Example 1: To list your custom output presets**

The following ``list-presets`` example lists your custom output presets. To list the system presets, see the next example. ::

    aws mediaconvert list-presets \
        --endpoint-url https://abcd1234.mediaconvert.us-west-2.amazonaws.com

Output::

    {
        "Presets": [
            {
                "Name": "SimpleMP4",
                "CreatedAt": 1568841521,
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
                "Arn": "arn:aws:mediaconvert:us-west-2:123456789012:presets/SimpleMP4",
                "Type": "CUSTOM",
                "LastUpdated": 1568843141,
                "Description": "Creates basic MP4 file. No filtering or preproccessing."
            },
            {
                "Name": "SimpleTS",
                "CreatedAt": 1568843113,
                "Settings": {
                    "ContainerSettings": {
                        "Container": "M2TS",
                        "M2tsSettings": {
                            "RateMode": "CBR"
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
                "Arn": "arn:aws:mediaconvert:us-west-2:123456789012:presets/SimpleTS",
                "Type": "CUSTOM",
                "LastUpdated": 1568843113,
                "Description": "Create a basic transport stream."
            }
        ]
    }

**Example 2: To list the system output presets**

The following ``list-presets`` example lists the available MediaConvert system presets. To list your custom presets, see the previous example. ::

    aws mediaconvert list-presets \
        --list-by SYSTEM \
        --endpoint-url https://abcd1234.mediaconvert.us-west-2.amazonaws.com

Output::

    {
        "Presets": [
            {
                "Arn": "arn:aws:mediaconvert:us-west-2:123456789012:presets/System-Avc_16x9_1080p_29_97fps_8500kbps",
                "Name": "System-Avc_16x9_1080p_29_97fps_8500kbps",
                "CreatedAt": 1568321789,
                "Description": "Wifi, 1920x1080, 16:9, 29.97fps, 8500kbps",
                "LastUpdated": 1568321789,
                "Type": "SYSTEM",
                "Category": "HLS",
                "Settings": {
                    "ContainerSettings": {
                        "Container": "M3U8"
                    },
                    "VideoDescription": {
                        "Width": 1920,
                        "Height": 1080,
                        "CodecSettings": {
                            "Codec": "H_264",
                            "H264Settings": {
                                "Bitrate": 8500000,
                                "CodecProfile": "MAIN",
                                "RateControlMode": "CBR",
                                "FramerateControl": "SPECIFIED",
                                "FramerateNumerator": 30000,
                                "FramerateDenominator": 1001
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
            },
            {
                "Arn": "arn:aws:mediaconvert:us-west-2:123456789012:presets/System-Xdcam_HD_1080i_29_97fps_35mpbs",
                "Name": "System-Xdcam_HD_1080i_29_97fps_35mpbs",
                "CreatedAt": 1568321790,
                "Description": "XDCAM MPEG HD, 1920x1080i, 29.97fps, 35mbps",
                "LastUpdated": 1568321790,
                "Type": "SYSTEM",
                "Category": "MXF",
                "Settings": {
                    "ContainerSettings": {
                        "Container": "MXF"
                    },
                    "VideoDescription": {
                        "Width": 1920,
                        "Height": 1080,
                        "CodecSettings": {
                            "Codec": "MPEG2",
                            "Mpeg2Settings": {
                                "Bitrate": 35000000,
                                "CodecLevel": "HIGH",
                                "CodecProfile": "MAIN",
                                "InterlaceMode": "TOP_FIELD",
                                "RateControlMode": "VBR",
                                "MaxBitrate": 35000000,
                                "FramerateControl": "SPECIFIED",
                                "FramerateNumerator": 30000,
                                "FramerateDenominator": 1001
                            }
                        }
                    },
                    "AudioDescriptions": [
                        {
                            "CodecSettings": {
                                "Codec": "WAV",
                                "WavSettings": {
                                    "BitDepth": 24,
                                    "Channels": 2,
                                    "SampleRate": 48000
                                }
                            }
                        }
                    ]
                }
            }
        ]
    }

For more information, see `Working with AWS Elemental MediaConvert Output Presets <https://docs.aws.amazon.com/mediaconvert/latest/ug/working-with-presets.html>`__ in the *AWS Elemental MediaConvert User Guide*.
