**To update a channel's configuration information**

The following ``update-channel`` example updates the channel configuration for a specified channel ARN (Amazon Resource Name). This does not affect an ongoing stream of this channel; you must stop and restart the stream for the changes to take effect. ::

    aws ivs update-channel \
        --arn arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh \
        --name "channel-1"

Output::

    {
        "channel": {
            "arn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh",
            "name": "channel-1",
            "latencyMode": "LOW",
            "ingestEndpoint": "a1b2c3d4e5f6.global-contribute.live-video.net",
            "playbackUrl": "https://a1b2c3d4e5f6.us-west-2.playback.live-video.net/api/video/v1/us-west-2.123456789012.channel.abcdEFGH.m3u8",
            "tags": {}
    }

For more information, see `Create a Channel <https://docs.aws.amazon.com/ivs/latest/userguide/GSIVS-create-channel.html>`__ in the *Amazon Interactive Video Service User Guide*.