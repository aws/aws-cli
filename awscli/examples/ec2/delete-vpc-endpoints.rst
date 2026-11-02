**To delete an endpoint**

The following ``delete-vpc-endpoints`` example deletes endpoints vpce-aa22bb33 and vpce-1a2b3c4d. If the command is partially successful or unsuccessful, a list of unsuccessful items is returned. If the command succeeds, the returned list is empty. ::

    aws ec2 delete-vpc-endpoints \
        --vpc-endpoint-ids vpce-aa22bb33 vpce-1a2b3c4d

Output::

    {
        "Unsuccessful": []
    }

For more information, see `Delete an interface endpoint <https://docs.aws.amazon.com/vpc/latest/privatelink/delete-interface-endpoint.html>`__ in the *AWS PrivateLink User Guide*.
