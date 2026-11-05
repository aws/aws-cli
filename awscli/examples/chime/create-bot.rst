**To create an Amazon Chime bot**

The following ``create-bot`` example creates a bot for the specified Amazon Chime Enterprise account. ::

    aws chime create-bot \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --display-name "myBot" \
        --domain "example.com"

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

For more information, see `Step 1: Integrate a chatbot with Amazon Chime <https://docs.aws.amazon.com/chime/latest/ag/integrate-bots.html>`__ in the *Amazon Chime Administration Guide*.
