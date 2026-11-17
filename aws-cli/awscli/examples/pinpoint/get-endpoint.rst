**To retrieve information about the settings and attributes of a specific endpoint for an application**

The following ``get-endpoint`` example retrieves information about the settings and attributes of a specific endpoint for an application. ::

    aws pinpoint get-endpoint \
        --application-id 611e3e3cdd47474c9c1399a505665b91 \
        --endpoint-id testendpoint

Output::

    {
        "EndpointResponse": {
            "Address": "+11234567890",
            "ApplicationId": "611e3e3cdd47474c9c1399a505665b91",
            "Attributes": {},
            "ChannelType": "SMS",
            "CohortId": "63",
            "CreationDate": "2019-01-28T23:55:11.534Z",
            "EffectiveDate": "2021-08-06T00:04:51.763Z",
            "EndpointStatus": "ACTIVE",
            "Id": "testendpoint",
            "Location": {
                "Country": "USA"
            },
            "Metrics": {
                "SmsDelivered": 1.0
            },
            "OptOut": "ALL",
            "RequestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "User": {
                "UserAttributes": {
                    "Age": [
                        "24"
                    ]
                },
            "UserId": "testuser"
            }
        }
    }

For more information, see `Add endpoints to Amazon Pinpoint <https://docs.aws.amazon.com/pinpoint/latest/developerguide/audience-define-endpoints.html>`__ in the *Amazon Pinpoint Developer Guide*.
