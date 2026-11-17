**To view the IP address CIDRs discovered by an IPAM**

The following ``get-ipam-discovered-resource-cidrs`` example lists the IP addresses for resources that the IPAM is discovering. In this example, you're an IPAM delegated admin who wants to view details related to these IP address CIDRs.

To complete this request, the resource discovery you choose must be associated with the IPAM, and the ``--resource-region`` is the AWS Region where the resource was created. ::

    aws ec2 get-ipam-discovered-resource-cidrs \
        --ipam-resource-discovery-id ipam-res-disco-0365d2977fc1672fe \
        --resource-region us-west-2

Output::

    {
        "IpamDiscoveredResourceCidrs": [
            {
                "IpamResourceDiscoveryId": "ipam-res-disco-0365d2977fc1672fe",
                "ResourceRegion": "us-west-2",
                "ResourceId": "vpc-0c974c95ca7ceef4a",
                "ResourceOwnerId": "123456789012",
                "ResourceCidr": "172.31.0.0/16",
                "ResourceType": "vpc",
                "ResourceTags": [],
                "IpUsage": 0.375,
                "VpcId": "vpc-0c974c95ca7ceef4a",
                "SampleTime": "2024-02-09T19:15:16.529000+00:00"
            },
            {
                "IpamResourceDiscoveryId": "ipam-res-disco-0365d2977fc1672fe",
                "ResourceRegion": "us-west-2",
                "ResourceId": "subnet-07fe028119082a8c1",
                "ResourceOwnerId": "123456789012",
                "ResourceCidr": "172.31.0.0/20",
                "ResourceType": "subnet",
                "ResourceTags": [],
                "IpUsage": 0.0012,
                "VpcId": "vpc-0c974c95ca7ceef4a",
                "SampleTime": "2024-02-09T19:15:16.529000+00:00"
            },
            {
                "IpamResourceDiscoveryId": "ipam-res-disco-0365d2977fc1672fe",
                "ResourceRegion": "us-west-2",
                "ResourceId": "subnet-0a96893763984cc4e",
                "ResourceOwnerId": "123456789012",
                "ResourceCidr": "172.31.64.0/20",
                "ResourceType": "subnet",
                "ResourceTags": [],
                "IpUsage": 0.0012,
                "VpcId": "vpc-0c974c95ca7ceef4a",
                "SampleTime": "2024-02-09T19:15:16.529000+00:00"
            }
        ]
    }

For more information, see `Monitor CIDR usage by resource <https://docs.aws.amazon.com/vpc/latest/ipam/monitor-cidr-compliance-ipam.html>`__ in the *Amazon VPC IPAM User Guide*.
