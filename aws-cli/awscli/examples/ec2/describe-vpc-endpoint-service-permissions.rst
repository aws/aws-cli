**To describe endpoint service permissions**

The following ``describe-vpc-endpoint-service-permissions`` example describes the permissions for the specified endpoint service. ::

    aws ec2 describe-vpc-endpoint-service-permissions \
        --service-id vpce-svc-03d5ebb7d9579a2b3

Output::

    {
        "AllowedPrincipals": [
            {
                "PrincipalType": "Account",
                "Principal": "arn:aws:iam::123456789012:root"
            }
        ]
    }

For more information, see `Manage permissions <https://docs.aws.amazon.com/vpc/latest/privatelink/configure-endpoint-service.html#add-remove-permissions>`__ in the *AWS PrivateLink User Guide*.
