**To retrieve details about a bot**

The following ``get-bot`` example displays the details for the specified bot. ::

    aws chime get-bot \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --bot-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "Bot": {
            "BotId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "UserId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "DisplayName": "myBot (Bot)",
            "BotType": "ChatBot",
            "Disabled": false,
            "CreatedTimestamp": "2019-09-09T18:05:56.749Z",
            "UpdatedTimestamp": "2019-09-09T18:05:56.749Z",
            "BotEmail": "myBot-chimebot@example.com",
            "SecurityToken": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        }
    }

For more information, see `Update chatbots <https://docs.aws.amazon.com/chime/latest/ag/update-bots.html>`__ in the *Amazon Chime Administration Guide*.
