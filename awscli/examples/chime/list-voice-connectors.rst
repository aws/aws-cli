**To list Amazon Chime Voice Connectors for an account**

The following ``list-voice-connectors`` example lists the Amazon Chime Voice Connectors associated with the administrator's account. ::

    aws chime list-voice-connectors

Output::

    {
        "VoiceConnectors": [
            {
                "VoiceConnectorId": "abcdef1ghij2klmno3pqr4",
                "Name": "MyVoiceConnector",
                "OutboundHostName": "abcdef1ghij2klmno3pqr4.voiceconnector.chime.aws",
                "RequireEncryption": true,
                "CreatedTimestamp": "2019-06-04T18:46:56.508Z",
                "UpdatedTimestamp": "2019-08-09T21:47:48.641Z"
            }
        ]
    }

For more information, see `Working with Amazon Chime Voice Connectors <https://docs.aws.amazon.com/chime/latest/ag/voice-connectors.html>`__ in the *Amazon Chime Administration Guide*.
