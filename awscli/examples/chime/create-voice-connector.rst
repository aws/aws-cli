**To create an Amazon Chime Voice Connector**

The following ``create-voice-connector`` example creates an Amazon Chime Voice Connector with encryption enabled. ::

    aws chime create-voice-connector \
        --name Test \
        --require-encryption

Output::

    {
        "VoiceConnector": {
            "VoiceConnectorId": "abcdef1ghij2klmno3pqr4",
            "Name": "Test",
            "OutboundHostName": "abcdef1ghij2klmno3pqr4.voiceconnector.chime.aws",
            "RequireEncryption": true,
            "CreatedTimestamp": "2019-06-04T18:46:56.508Z",
            "UpdatedTimestamp": "2019-06-04T18:46:56.508Z"
        }
    }

For more information, see `Working with Amazon Chime Voice Connectors <https://docs.aws.amazon.com/chime/latest/ag/voice-connectors.html>`__ in the *Amazon Chime Administration Guide*.
