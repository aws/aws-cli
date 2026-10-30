**To reject an interface endpoint connection request**

The following ``reject-vpc-endpoint-connections`` example rejects the specified endpoint connection request for the specified endpoint service. ::

    aws ec2 reject-vpc-endpoint-connections \
        --service-id vpce-svc-03d5ebb7d9579a2b3 \
        --vpc-endpoint-ids vpce-0c1308d7312217abc

Output::

    {
        "Unsuccessful": []
    }

For more information, see `Configure an endpoint service <https://docs.aws.amazon.com/vpc/latest/privatelink/configure-endpoint-service.html#accept-reject-connection-requests>`__ in the *AWS PrivateLink User Guide*.
