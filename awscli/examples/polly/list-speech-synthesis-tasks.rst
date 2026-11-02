**To list your speech synthesis tasks**

The following ``list-speech-synthesis-tasks`` example lists your speech synthesis tasks. ::

    aws polly list-speech-synthesis-tasks 

Output::

    {
        "SynthesisTasks": [
            {
                "TaskId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "TaskStatus": "completed",
                "OutputUri": "https://s3.us-west-2.amazonaws.com/amzn-s3-demo-bucket/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111.mp3",
                "CreationTime": 1603911042.689,
                "RequestCharacters": 1311,
                "OutputFormat": "mp3",
                "TextType": "text",
                "VoiceId": "Joanna"
            }
        ]
    }

For more information, see `Creating long audio files <https://docs.aws.amazon.com/polly/latest/dg/longer-console.html>`__ in the *Amazon Polly Developer Guide*.

