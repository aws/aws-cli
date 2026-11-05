**To create an endpoint connection notification**

The following ``create-vpc-endpoint-connection-notification`` example creates a notification for a specific endpoint service that alerts you when interface endpoints have connected to your service and when endpoints have been accepted for your service. ::

    aws ec2 create-vpc-endpoint-connection-notification \
        --connection-notification-arn arn:aws:sns:us-west-2:123456789012:VpceNotification \
        --connection-events Connect Accept \
        --service-id vpce-svc-1237881c0d25a3abc

Output::

    {
        "ConnectionNotification": {
            "ConnectionNotificationState": "Enabled",
            "ConnectionNotificationType": "Topic",
            "ServiceId": "vpce-svc-1237881c0d25a3abc",
            "ConnectionEvents": [
                "Accept",
                "Connect"
            ],
            "ConnectionNotificationId": "vpce-nfn-008776de7e03f5abc",
            "ConnectionNotificationArn": "arn:aws:sns:us-west-2:123456789012:VpceNotification"
        }
    }

For more information, see `Receive alerts for endpoint service events <https://docs.aws.amazon.com/vpc/latest/privatelink/create-notification-endpoint-service.html>`__ in the *AWS PrivateLink User Guide*.
