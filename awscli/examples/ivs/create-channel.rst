**Example 1: To create a channel with no recording**

The following ``create-channel`` example creates a new channel and an associated stream key to start streaming. ::

    aws ivs create-channel \
        --name "test-channel" \
        --no-insecure-ingest

Output::

    {
        "channel": {
            "arn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh",
            "authorized": false,
            "name": "test-channel",
            "latencyMode": "LOW",
            "playbackRestrictionPolicyArn": "",
            "recordingConfigurationArn": "",
            "srt": {
                "endpoint": "a1b2c3d4e5f6.srt.live-video.net",
                "passphrase": "AB1C2defGHijkLMNo3PqQRstUvwxyzaBCDEfghh4ijklMN5opqrStuVWxyzAbCDEfghIJ"
            },
            "ingestEndpoint": "a1b2c3d4e5f6.global-contribute.live-video.net",
            "insecureIngest": false,
            "playbackUrl": "https://a1b2c3d4e5f6.us-west-2.playback.live-video.net/api/video/v1/us-west-2.123456789012.channel.abcdEFGH.m3u8",
            "preset": "",
            "tags": {},
            "type": "STANDARD"
        },
        "streamKey": {
            "arn": "arn:aws:ivs:us-west-2:123456789012:stream-key/g1H2I3j4k5L6",
            "value": "sk_us-west-2_abcdABCDefgh_567890abcdef",
            "channelArn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh",
            "tags": {}
        }
    }

For more information, see `Create a Channel <https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/getting-started-create-channel.html>`__ in the *IVS Low-Latency User Guide*.

**Example 2: To create a channel with recording enabled, using the RecordingConfiguration resource specified by its ARN**

The following ``create-channel`` example creates a new channel and an associated stream key to start streaming, and sets up recording for the channel. ::

    aws ivs create-channel \
        --name test-channel-with-recording \
        --insecure-ingest \
        --recording-configuration-arn "arn:aws:ivs:us-west-2:123456789012:recording-configuration/ABCD12cdEFgh"

Output::

    {
        "channel": {
            "arn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh",
            "name": "test-channel-with-recording",
            "latencyMode": "LOW",
            "type": "STANDARD",
            "playbackRestrictionPolicyArn": "",
            "recordingConfigurationArn": "arn:aws:ivs:us-west-2:123456789012:recording-configuration/ABCD12cdEFgh",
            "srt": {
                "endpoint": "a1b2c3d4e5f6.srt.live-video.net",
                "passphrase": "BA1C2defGHijkLMNo3PqQRstUvwxyzaBCDEfghh4ijklMN5opqrStuVWxyzAbCDEfghIJ"
            },
            "ingestEndpoint": "a1b2c3d4e5f6.global-contribute.live-video.net",
            "insecureIngest": true,
            "playbackUrl": "https://a1b2c3d4e5f6.us-west-2.playback.live-video.net/api/video/v1/us-west-2.123456789012.channel.abcdEFGH.m3u8",
            "preset": "",
            "authorized": false,
            "tags": {},
            "type": "STANDARD"
        },
        "streamKey": {
            "arn": "arn:aws:ivs:us-west-2:123456789012:stream-key/abcdABCDefgh",
            "value": "sk_us-west-2_abcdABCDefgh_567890abcdef",
            "channelArn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh",
            "tags": {}
        }
    }

For more information, see `Record to Amazon S3 <https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/record-to-s3.html>`__ in the *IVS Low-Latency User Guide*.

**Example 3: To create a channel with a playback restriction policy specified by its ARN**

The following ``create-channel`` example creates a new channel and an associated stream key to start streaming, and sets up a playback restriction policy for the channel. ::

    aws ivs create-channel \
        --name test-channel-with-playback-restriction-policy \
        --insecure-ingest \
        --playback-restriction-policy-arn "arn:aws:ivs:us-west-2:123456789012:playback-restriction-policy/ABcdef34ghIJ"

Output::

    {
        "channel": {
            "arn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh",
            "name": "test-channel-with-playback-restriction-policy",
            "latencyMode": "LOW",
            "type": "STANDARD",
            "playbackRestrictionPolicyArn": "arn:aws:ivs:us-west-2:123456789012:playback-restriction-policy/ABcdef34ghIJ",
            "recordingConfigurationArn": "",
            "srt": {
                "endpoint": "a1b2c3d4e5f6.srt.live-video.net",
                "passphrase": "AB1C2edfGHijkLMNo3PqQRstUvwxyzaBCDEfghh4ijklMN5opqrStuVWxyzAbCDEfghIJ"
            },
            "ingestEndpoint": "a1b2c3d4e5f6.global-contribute.live-video.net",
            "insecureIngest": true,
            "playbackUrl": "https://a1b2c3d4e5f6.us-west-2.playback.live-video.net/api/video/v1/us-west-2.123456789012.channel.abcdEFGH.m3u8",
            "preset": "",
            "authorized": false,
            "tags": {},
            "type": "STANDARD"
        },
        "streamKey": {
            "arn": "arn:aws:ivs:us-west-2:123456789012:stream-key/abcdABCDefgh",
            "value": "sk_us-west-2_abcdABCDefgh_567890abcdef",
            "channelArn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh",
            "tags": {}
        }
    }

For more information, see `Undesired Content and Viewers <https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/undesired-content.html>`__ in the *IVS Low-Latency User Guide*.