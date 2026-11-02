**To get information about a speech synthesis task**

The following ``get-speech-synthesis-task`` example retrieves information about the specified speech synthesis task. ::

    aws polly get-speech-synthesis-task \
        --task-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "SynthesisTask": {
            "TaskId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "TaskStatus": "completed",
            "OutputUri": "https://s3.us-west-2.amazonaws.com/amzn-s3-demo-bucket/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111.mp3",
            "CreationTime": 1603911042.689,
            "RequestCharacters": 1311,
            "OutputFormat": "mp3",
            "TextType": "text",
            "VoiceId": "Joanna"
        }
    }

For more information, see `Creating long audio files <https://docs.aws.amazon.com/polly/latest/dg/longer-console.html>`__ in the *Amazon Polly Developer Guide*.
