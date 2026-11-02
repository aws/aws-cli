**To disassociate a resource discovery from an IPAM**

The following ``disassociate-ipam-resource-discovery`` example disassociates an IPAM resource discovery in your AWS account. In this example, you are an IPAM delegated admin account and you want to disassociate an IPAM resource discovery from your IPAM. You ran the describe command and noticed that the ``"ResourceDiscoveryStatus": "not-found"`` and you want to disassociate it from your IPAM to make room for other associations. ::

    aws ec2 disassociate-ipam-resource-discovery \
        --ipam-resource-discovery-association-id ipam-res-disco-assoc-04382a6346357cf82

Output::

    {
        "IpamResourceDiscoveryAssociation": {
            "OwnerId": "123456789012",
            "IpamResourceDiscoveryAssociationId": "ipam-res-disco-assoc-04382a6346357cf82",
            "IpamResourceDiscoveryAssociationArn":             "arn:aws:ec2::123456789012:ipam-resource-discovery-association/ipam-res-disco-assoc-04382a6346357cf82",
            "IpamResourceDiscoveryId": "ipam-res-disco-0365d2977fc1672fe",
            "IpamId": "ipam-005f921c17ebd5107",
            "IpamArn": "arn:aws:ec2::123456789012:ipam/ipam-005f921c17ebd5107",
            "IpamRegion": "us-west-2",
            "IsDefault": false,
            "ResourceDiscoveryStatus": "not-found",
            "State": "disassociate-in-progress"
        }
    }

For more information, see `Integrate IPAM with accounts outside of your organization <https://docs.aws.amazon.com/vpc/latest/ipam/enable-integ-ipam-outside-org.html>`__ in the *Amazon VPC IPAM User Guide*.