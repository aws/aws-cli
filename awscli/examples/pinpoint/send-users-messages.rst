**To send SMS message for an user of an application**

The following ``send-users-messages`` example sends a direct message for an user of an application. ::

    aws pinpoint send-users-messages \
        --application-id 611e3e3cdd47474c9c1399a505665b91 \
        --send-users-message-request file://myfile.json

Contents of ``myfile.json``::

    {
        "MessageConfiguration": {
            "SMSMessage": {
                "Body": "hello, how are you?"
            }
        },
        "Users": {
            "testuser": {}
        }
    }

Output::

    {
        "SendUsersMessageResponse": {
            "ApplicationId": "611e3e3cdd47474c9c1399a505665b91",
            "RequestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Result": {
                "testuser": {
                    "testuserendpoint": {
                        "DeliveryStatus": "SUCCESSFUL",
                        "MessageId": "7qu4hk5bqhda3i7i2n4pjf98qcuh8b7p45ifsmo0",
                        "StatusCode": 200,
                        "StatusMessage": "MessageId: 7qu4hk5bqhda3i7i2n4pjf98qcuh8b7p45ifsmo0",
                        "Address": "+12345678900"
                    }
                }
            }
        }
    }

For more information, see `Amazon Pinpoint SMS channel <https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms.html>`__ in the *Amazon Pinpoint User Guide*.