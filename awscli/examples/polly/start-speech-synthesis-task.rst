**To synthesize text**

The following ``start-speech-synthesis-task`` example synthesizes the text in ``text_file.txt`` and stores the resulting MP3 file in the specified bucket. ::

    aws polly start-speech-synthesis-task \
        --output-format mp3 \
        --output-s3-bucket-name amzn-s3-demo-bucket \
        --text  file://text_file.txt \
        --voice-id Joanna

Contents of ``text_file.txt``::

    Amazon Polly is a service that turns text into lifelike speech. With
    asynchronous synthesis tasks, you can convert long documents, such as
    articles, book chapters, and training material, into a single audio file
    that is stored in the Amazon S3 bucket that you specify. Synchronous
    requests are limited in the amount of text that they can process, so
    asynchronous tasks are the better choice when you have a large amount of
    text to synthesize. When you start a task, Amazon Polly returns a task ID
    right away and continues to process the text in the background. You can use
    the task ID to check the status of the task at any time. When the task is
    complete, the audio file is available in the output bucket, and you can
    download it, play it in an application, or share it with your users. You can
    also have Amazon Polly send a notification to an Amazon SNS topic when the
    task finishes, so that you do not have to check the status yourself. Amazon
    Polly supports many languages and voices, and you can choose the voice that
    best fits your content. For example, you might use one voice for a news
    article and a different voice for a story for children. You can also use
    SSML tags to control how the text is spoken, such as adding pauses or
    changing the speaking rate. This makes it simple to create audio content.

Output::

    {
        "SynthesisTask": {
            "TaskId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "TaskStatus": "scheduled",
            "OutputUri": "https://s3.us-west-2.amazonaws.com/amzn-s3-demo-bucket/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111.mp3",
            "CreationTime": 1603911042.689,
            "RequestCharacters": 1311,
            "OutputFormat": "mp3",
            "TextType": "text",
            "VoiceId": "Joanna"
        }
    }

For more information, see `Creating long audio files <https://docs.aws.amazon.com/polly/latest/dg/longer-console.html>`__ in the *Amazon Polly Developer Guide*.

