**To update the details for an Amazon Chime Voice Connector**

The following ``update-voice-connector`` example updates the name of the specified Amazon Chime Voice Connector. ::

    aws chime update-voice-connector \
        --voice-connector-id abcdef1ghij2klmno3pqr4 \
        --name MyVoiceConnector \
        --require-encryption

Output::

    {
        "VoiceConnector": {
            "VoiceConnectorId": "abcdef1ghij2klmno3pqr4",
            "Name": "MyVoiceConnector",
            "OutboundHostName": "abcdef1ghij2klmno3pqr4.voiceconnector.chime.aws",
            "RequireEncryption": true,
            "CreatedTimestamp": "2019-06-04T18:46:56.508Z",
            "UpdatedTimestamp": "2019-08-09T21:47:48.641Z"
        }
    }

For more information, see `Working with Amazon Chime Voice Connectors <https://docs.aws.amazon.com/chime/latest/ag/voice-connectors.html>`__ in the *Amazon Chime Administration Guide*.
