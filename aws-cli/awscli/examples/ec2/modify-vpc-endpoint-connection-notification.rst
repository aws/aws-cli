**To modify an endpoint connection notification**

The following ``modify-vpc-endpoint-connection-notification`` example changes the SNS topic for the specified endpoint connection notification. ::

    aws ec2 modify-vpc-endpoint-connection-notification \
        --connection-notification-id vpce-nfn-008776de7e03f5abc \
        --connection-events Accept Reject \
        --connection-notification-arn arn:aws:sns:us-west-2:123456789012:mytopic

Output::

    {
        "ReturnValue": true
    }

For more information, see `Receive alerts for endpoint service events <https://docs.aws.amazon.com/vpc/latest/privatelink/create-notification-endpoint-service.html>`__ in the *AWS PrivateLink User Guide*.
