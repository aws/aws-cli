**To retrieve information about the status and settings of the APNs channel for an application**

The following ``get-apns-channel`` example retrieves information about the status and settings of the APNs channel for an application. ::

    aws pinpoint get-apns-channel \
        --application-id 9ab1068eb0a6461c86cce7f27ce0efd7

Output::

    {
        "APNSChannelResponse": {
            "ApplicationId": "9ab1068eb0a6461c86cce7f27ce0efd7",
            "CreationDate": "2019-05-09T21:54:45.082Z",
            "DefaultAuthenticationMethod": "CERTIFICATE",
            "Enabled": true,
            "HasCredential": true,
            "HasTokenKey": false,
            "Id": "apns",
            "IsArchived": false,
            "LastModifiedDate": "2019-05-09T22:04:01.067Z",
            "Platform": "APNS",
            "Version": 2
        }
    }

For more information, see `Amazon Pinpoint push notifications <https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-push.html>`__ in the *Amazon Pinpoint User Guide*.
