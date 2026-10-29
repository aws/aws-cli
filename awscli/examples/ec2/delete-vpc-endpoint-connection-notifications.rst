**To delete an endpoint connection notification**

The following ``delete-vpc-endpoint-connection-notifications`` example deletes the specified endpoint connection notification. ::

    aws ec2 delete-vpc-endpoint-connection-notifications \
        --connection-notification-ids vpce-nfn-008776de7e03f5abc

Output::

    {
        "Unsuccessful": []
    }

For more information, see `Receive alerts for endpoint service events <https://docs.aws.amazon.com/vpc/latest/privatelink/create-notification-endpoint-service.html>`__ in the *AWS PrivateLink User Guide*.
