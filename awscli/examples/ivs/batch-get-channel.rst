**To get channel configuration information about multiple channels**

The following ``batch-get-channel`` example lists information about the specified channels. ::

    aws ivs batch-get-channel \
        --arns arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh \
            arn:aws:ivs:us-west-2:123456789012:channel/efghEFGHijkl

Output::

    {
        "channels": [
            {
                "arn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh",
                "name": "channel-1",
                "latencyMode": "LOW",
                "type": "STANDARD",
                "recordingConfigurationArn": "arn:aws:ivs:us-west-2:123456789012:recording-configuration/ABCD12cdEFgh",
                "ingestEndpoint": "a1b2c3d4e5f6.global-contribute.live-video.net",
                "insecureIngest": false,
                "playbackUrl": "https://a1b2c3d4e5f6.us-west-2.playback.live-video.net/api/video/v1/us-west-2.123456789012.channel-1.abcdEFGH.m3u8",
                "tags": {}
            },
            {
                "arn": "arn:aws:ivs:us-west-2:123456789012:channel/efghEFGHijkl",
                "name": "channel-2",
                "latencyMode": "LOW",
                "type": "STANDARD",
                "recordingConfigurationArn": "",
                "ingestEndpoint": "a1b2c3d4e5f6.global-contribute.live-video.net",
                "insecureIngest": true,
                "playbackUrl": "https://a1b2c3d4e5f6.us-west-2.playback.live-video.net/api/video/v1/us-west-2.123456789012.channel-2.abcdEFGH.m3u8",
                "tags": {}
            }
        ]
    }

For more information, see `Create a Channel <https://docs.aws.amazon.com/ivs/latest/userguide/GSIVS-create-channel.html>`__ in the *Amazon Interactive Video Service User Guide*.