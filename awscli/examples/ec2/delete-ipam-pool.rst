**To delete an IPAM pool**

The following ``delete-ipam-pool`` example deletes an IPAM pool in your AWS account. In this example, you're an IPAM delegated admin who wants to delete an IPAM pool that you no longer need, but the pool has a CIDR provisioned to it. You cannot delete a pool if it has CIDRs provisioned to it unless you use the ``--cascade`` option, so you'll use ``--cascade``.

To complete this request:

* You'll need the IPAM pool ID which you can get with `describe-ipam-pools <https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-ipam-pools.html>`__. 
* The ``--region`` must be the IPAM home Region.

To delete the pool, use the following command. ::

    aws ec2 delete-ipam-pool \
        --ipam-pool-id ipam-pool-050c886a3ca41cd5b \
        --cascade \
        --region us-west-2

Output::

    {
        "IpamPool": {
            "OwnerId": "123456789012",
            "IpamPoolId": "ipam-pool-050c886a3ca41cd5b",
            "IpamPoolArn": "arn:aws:ec2::123456789012:ipam-pool/ipam-pool-050c886a3ca41cd5b",
            "IpamScopeArn": "arn:aws:ec2::123456789012:ipam-scope/ipam-scope-0a158dde35c51107b",
            "IpamScopeType": "private",
            "IpamArn": "arn:aws:ec2::123456789012:ipam/ipam-005f921c17ebd5107",
            "IpamRegion": "us-west-2",
            "Locale": "None",
            "PoolDepth": 1,
            "State": "delete-in-progress",
            "Description": "example",
            "AutoImport": false,
            "AddressFamily": "ipv4",
            "AllocationMinNetmaskLength": 0,
            "AllocationMaxNetmaskLength": 32
        }
    }

For more information, see `Delete a pool <https://docs.aws.amazon.com/vpc/latest/ipam/delete-pool-ipam.html>`__ in the *Amazon VPC IPAM User Guide*.