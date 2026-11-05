**To delete an endpoint service configuration**

The following ``delete-vpc-endpoint-service-configurations`` example deletes the specified endpoint service configuration. ::

    aws ec2 delete-vpc-endpoint-service-configurations \
        --service-ids vpce-svc-03d5ebb7d9579a2b3

Output::

    {
        "Unsuccessful": []
    }

For more information, see `Delete an endpoint service <https://docs.aws.amazon.com/vpc/latest/privatelink/delete-endpoint-service.html>`__ in the *AWS PrivateLink User Guide*.
