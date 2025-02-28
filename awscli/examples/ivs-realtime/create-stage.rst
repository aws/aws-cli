**Example 1: To create a stage**

The following ``create-stage`` example creates a stage and stage participant token for a specified user. ::

    aws ivs-realtime create-stage \
        --name stage1 \
        --participant-token-configurations userId=alice

Output::

    {
        "participantTokens": [
            {
                "participantId": "ABCDEfghij01234KLMN5678",
                "token": "a1b2c3d4567890ab",
                "userId": "alice"
            }
        ],
        "stage": {
            "activeSessionId": "st-a1b2c3d4e5f6g",
            "arn": "arn:aws:ivs:us-west-2:123456789012:stage/abcdABCDefgh",
            "autoParticipantRecordingConfiguration": {
                "storageConfigurationArn": "",
                "mediaTypes": [
                    "AUDIO_VIDEO"
                ],
                "thumbnailConfiguration": {
                    "targetIntervalSeconds": 60,
                    "storage": [
                        "SEQUENTIAL"
                    ],
                    "recordingMode": "DISABLED"
                }
            },
            "endpoints": {
                "events": "wss://global.events.live-video.net",
                "rtmp": "rtmp://9x0y8z7s6t5u.global-contribute-staging.live-video.net/app/",
                "rtmps": "rtmps://9x0y8z7s6t5u.global-contribute-staging.live-video.net:443/app/",
                "whip": "https://9x0y8z7s6t5u.global-bm.whip.live-video.net"
            },
            "name": "stage1",
            "tags": {}
        }
    }

For more information, see `Enabling Multiple Hosts on an Amazon IVS Stream <https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/multiple-hosts.html>`__ in the *Amazon Interactive Video Service User Guide*.

**Example 2: To create a stage and configure individial participant recording**

The following ``create-stage`` example creates a stage and configures individual participant recording. ::

    aws ivs-realtime create-stage \
        --name stage1 \
        --auto-participant-recording-configuration '{"mediaTypes": ["AUDIO_VIDEO"],"storageConfigurationArn": "arn:aws:ivs:us-west-2:123456789012:storage-configuration/abcdABCDefgh"}'

Output::

    {
        "stage": { 
            "activeSessionId": "st-a1b2c3d4e5f6g",
            "arn": "arn:aws:ivs:us-west-2:123456789012:stage/abcdABCDefgh",
            "autoParticipantRecordingConfiguration": {
                "storageConfigurationArn": "arn:aws:ivs:us-west-2:123456789012:storage-configuration/abcdABCDefgh"
                "mediaTypes": [
                    "AUDIO_VIDEO"
                ],
                "thumbnailConfiguration": {
                    "targetIntervalSeconds": 60,
                    "storage": [
                        "SEQUENTIAL"
                    ],
                    "recordingMode": "DISABLED"
                }
            },            
            "endpoints": {
                "events": "wss://global.events.live-video.net",
                "rtmp": "rtmp://9x0y8z7s6t5u.global-contribute-staging.live-video.net/app/",
                "rtmps": "rtmps://9x0y8z7s6t5u.global-contribute-staging.live-video.net:443/app/",
                "whip": "https://9x0y8z7s6t5u.global-bm.whip.live-video.net"
            },
            "name": "stage1",
            "tags": {}
        }
    }

For more information, see `Enabling Multiple Hosts on an Amazon IVS Stream <https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/multiple-hosts.html>`__ in the *Amazon Interactive Video Service User Guide*.

**Example 3: To create a stage and configure individial participant recording with thumbnail recording enabled**

The following ``create-stage`` example creates a stage and configures individual participant recording with thumbnail recording enabled. ::

    aws ivs-realtime create-stage \
        --name stage1 \
        --auto-participant-recording-configuration '{"mediaTypes": ["AUDIO_VIDEO"],"storageConfigurationArn": "arn:aws:ivs:us-west-2:123456789012:storage-configuration/abcdABCDefgh", \
            "thumbnailConfiguration": {"recordingMode": "INTERVAL","storage": ["SEQUENTIAL"],"targetIntervalSeconds": 60}}'

Output::

    {
        "stage": { 
            "activeSessionId": "st-a1b2c3d4e5f6g",
            "arn": "arn:aws:ivs:us-west-2:123456789012:stage/abcdABCDefgh",
            "autoParticipantRecordingConfiguration": {
                "storageConfigurationArn": "arn:aws:ivs:us-west-2:123456789012:storage-configuration/abcdABCDefgh",
                "mediaTypes": [
                    "AUDIO_VIDEO"
                ],
                "thumbnailConfiguration": { 
                    "targetIntervalSeconds": 60,
                    "storage": [
                        "SEQUENTIAL"
                    ],
                    "recordingMode": "INTERVAL"
                }
            },            
            "endpoints": {
                "events": "wss://global.events.live-video.net",
                "rtmp": "rtmp://9x0y8z7s6t5u.global-contribute-staging.live-video.net/app/",
                "rtmps": "rtmps://9x0y8z7s6t5u.global-contribute-staging.live-video.net:443/app/",
                "whip": "https://9x0y8z7s6t5u.global-bm.whip.live-video.net"
            },
            "name": "stage1",
            "tags": {}
        }
    }

For more information, see `Enabling Multiple Hosts on an Amazon IVS Stream <https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/multiple-hosts.html>`__ in the *Amazon Interactive Video Service User Guide*.