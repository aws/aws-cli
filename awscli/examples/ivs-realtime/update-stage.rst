**To update a stage's configuration**

The following ``update-stage`` example updates a stage for a specified stage ARN to update the stage name and configure individual participant recording. ::

    aws ivs-realtime update-stage \
        --arn arn:aws:ivs:us-west-2:123456789012:stage/abcdABCDefgh \
        --auto-participant-recording-configuration '{"mediaTypes": ["AUDIO_VIDEO"],"storageConfigurationArn": "arn:aws:ivs:us-west-2:123456789012:storage-configuration/abcdABCDefgh"}' \
        --name stage1a

Output::

    {
        "stage": {
            "arn": "arn:aws:ivs:us-west-2:123456789012:stage/abcdABCDefgh",
            "autoParticipantRecordingConfiguration": {
                 "mediaTypes": [
                       "AUDIO_VIDEO"
                 ],
                 "storageConfigurationArn": "arn:aws:ivs:us-west-2:123456789012:storage-configuration/abcdABCDefgh",
            },
            "endpoints": {
                "events": "wss://global.events.live-video.net",
                "whip": "https://1a2b3c4d5e6f.global-bm.whip.live-video.net"
            },
            "name": "stage1a",
            "tags": {}
        }
    }

For more information, see `Enabling Multiple Hosts on an Amazon IVS Stream <https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/multiple-hosts.html>`__ in the *Amazon Interactive Video Service User Guide*.