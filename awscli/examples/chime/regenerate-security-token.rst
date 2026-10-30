**To regenerate a security token**

The following ``regenerate-security-token`` example regenerates the security token for the specified bot. ::

    aws chime regenerate-security-token \
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
            "SecurityToken": "je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY"
        }
    }


For more information, see `Authenticate chatbot requests <https://docs.aws.amazon.com/chime/latest/ag/auth-bots.html>`__ in the *Amazon Chime Administration Guide*.
