**Example 1: To view complete details of resource discoveries**

The following ``describe-ipam-resource-discoveries`` example lists the details of the resource discovery in your AWS account. You can have one resource discovery per AWS Region.

In this example, you're a delegated IPAM admin who wants to create and share a resource discovery with the IPAM admin in another AWS Organization so that the admin can manage and monitor the IP addresses of resources in your organization.

This example may be useful if:

* You tried to create a resource discovery, but you got an error that you've reached your limit of 1. You realize that you may have already created a resource discovery and you want to view it in your account.
* You have resources in a Region that are not being discovered by the IPAM. You want to view the ``--operating-regions`` defined for the resource and ensure that you've added the right Region as an operating Region so that the resources there can be discovered.

To view the resource discovery in the ``us-west-2`` Region, use the following command. ::

    aws ec2 describe-ipam-resource-discoveries

Output::

    {
        "IpamResourceDiscoveries": [
            {
                "OwnerId": "123456789012",
                "IpamResourceDiscoveryId": "ipam-res-disco-0f8bdee9067137c0d",
                "IpamResourceDiscoveryArn": "arn:aws:ec2::123456789012:ipam-resource-discovery/ipam-res-disco-0f8bdee9067137c0d",
                "IpamResourceDiscoveryRegion": "us-west-2",
                "OperatingRegions": [
                    {
                        "RegionName": "us-west-2"
                    }
                ],
                "IsDefault": false,
                "State": "create-complete",
                "Tags": []
        }
    ]
    }

For more information, see `Integrate IPAM with accounts outside of your organization <https://docs.aws.amazon.com/vpc/latest/ipam/enable-integ-ipam-outside-org.html>`__ in the *Amazon VPC IPAM User Guide*.

**Example 2: To view only resource discovery IDs**

The following ``describe-ipam-resource-discoveries`` example lists the ID of the resource discovery in your AWS account. You can have one resource discovery per AWS Region. ::

    aws ec2 describe-ipam-resource-discoveries \
        --query "IpamResourceDiscoveries[*].IpamResourceDiscoveryId"

Output::

    [
        "ipam-res-disco-0481e39b242860333"
    ]

For more information, see `Integrate IPAM with accounts outside of your organization <https://docs.aws.amazon.com/vpc/latest/ipam/enable-integ-ipam-outside-org.html>`__ in the *Amazon VPC IPAM User Guide*.