**To modify an endpoint service configuration**

The following ``modify-vpc-endpoint-service-configuration`` example changes the acceptance requirement for the specified endpoint service. ::

    aws ec2 modify-vpc-endpoint-service-configuration \
        --service-id vpce-svc-09222513e6e77dc86 \
        --no-acceptance-required

Output::

    {
        "Return": true
    }

For more information, see `Configure an endpoint service <https://docs.aws.amazon.com/vpc/latest/privatelink/configure-endpoint-service.html>`__ in the *AWS PrivateLink User Guide*.
