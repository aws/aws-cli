**To retrieve a list of bots**

The following ``list-bots`` example lists the bots associated with the specified Amazon Chime Enterprise account. ::

    aws chime list-bots \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Bots": [
            {
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
        ]
    }

For more information, see `Use Chat Bots with Amazon Chime <https://docs.aws.amazon.com/chime/latest/dg/use-bots.html>`__ in the *Amazon Chime Developer Guide*.
