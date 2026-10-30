**To modify endpoint service permissions**

The following ``modify-vpc-endpoint-service-permissions`` example adds permission for an AWS account to connect to the specified endpoint service. ::

    aws ec2 modify-vpc-endpoint-service-permissions \
        --service-id vpce-svc-03d5ebb7d9579a2b3 \
        --add-allowed-principals '["arn:aws:iam::123456789012:root"]'

Output::

    {
        "ReturnValue": true
    }

The following ``modify-vpc-endpoint-service-permissions`` example adds permission for a specific IAM user (``admin``) to connect to the specified endpoint service. ::

    aws ec2 modify-vpc-endpoint-service-permissions \
        --service-id vpce-svc-03d5ebb7d9579a2b3 \
        --add-allowed-principals '["arn:aws:iam::123456789012:user/admin"]'

For more information, see `Configure an endpoint service <https://docs.aws.amazon.com/vpc/latest/privatelink/configure-endpoint-service.html#add-remove-permissions>`__ in the *AWS PrivateLink User Guide*.
