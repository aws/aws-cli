**To modify the description of a scope**

The following ``modify-ipam-scope`` example updates the description of an IPAM scope. In this scenario, you're an IPAM delegated admin.

To complete this request, you'll need the scope ID, which you can get with `describe-ipam-scopes <https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-ipam-scopes.html>`__. ::

    aws ec2 modify-ipam-scope \
        --ipam-scope-id ipam-scope-0d3539a30b57dcdd1 \
        --description example

Output::

    {
        "IpamScope": {
            "OwnerId": "123456789012",
            "IpamScopeId": "ipam-scope-0d3539a30b57dcdd1",
            "IpamScopeArn": "arn:aws:ec2::123456789012:ipam-scope/ipam-scope-0d3539a30b57dcdd1",
            "IpamArn": "arn:aws:ec2::123456789012:ipam/ipam-005f921c17ebd5107",
            "IpamRegion": "us-west-2",
            "IpamScopeType": "public",
            "IsDefault": true,
            "Description": "example",
            "PoolCount": 1,
            "State": "modify-in-progress"
        }
    }

For more information about scopes, see `How IPAM works <https://docs.aws.amazon.com/vpc/latest/ipam/how-it-works-ipam.html>`__ in the *Amazon VPC IPAM User Guide*.
