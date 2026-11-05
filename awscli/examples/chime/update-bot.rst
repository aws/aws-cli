**To update a bot**

The following ``update-bot`` example updates the status of the specified bot to stop it from running. ::

    aws chime update-bot \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --bot-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --disabled

Output::

    {
        "Bot": {
            "BotId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "UserId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "DisplayName": "myBot (Bot)",
            "BotType": "ChatBot",
            "Disabled": true,
            "CreatedTimestamp": "2019-09-09T18:05:56.749Z",
            "UpdatedTimestamp": "2019-09-09T18:05:56.749Z",
            "BotEmail": "myBot-chimebot@example.com",
            "SecurityToken": "je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY"
        }
    }

For more information, see `Update chatbots <https://docs.aws.amazon.com/chime/latest/ag/update-bots.html>`__ in the *Amazon Chime Administration Guide*.
