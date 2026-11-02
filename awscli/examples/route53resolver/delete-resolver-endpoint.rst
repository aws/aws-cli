**To delete a Resolver endpoint**

The following ``delete-resolver-endpoint`` example deletes the specified endpoint. 

**Important** If you delete an inbound endpoint, DNS queries from your network are no longer forwarded to Resolver in the VPC that you specified in the endpoint. If you delete an outbound endpoint, Resolver stops forwarding DNS queries from your VPC to your network for rules that specify the deleted outbound endpoint. ::

    aws route53resolver delete-resolver-endpoint \
        --resolver-endpoint-id rslvr-in-497098ad59example

Output::

    {
        "ResolverEndpoint": {
            "Id": "rslvr-in-497098ad59example",
            "CreatorRequestId": "AWSConsole.25.157290example",
            "Arn": "arn:aws:route53resolver:us-west-2:123456789012:resolver-endpoint/rslvr-in-497098ad59example",
            "Name": "my-inbound-endpoint",
            "SecurityGroupIds": [
                "sg-05cd7b25d6example"
            ],
            "Direction": "INBOUND",
            "IpAddressCount": 5,
            "HostVPCId": "vpc-304bexam",
            "Status": "DELETING",
            "StatusMessage": "[Trace id: 1-5dc5b658-811b5be0922bbc382example] Deleting ResolverEndpoint.",
            "CreationTime": "2020-01-01T23:25:45.538Z",
            "ModificationTime": "2020-01-02T23:25:45.538Z"
        }
    }

For more information, see `Managing inbound endpoints <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-inbound-queries-managing.html#resolver-forwarding-inbound-queries-managing-deleting>`__ in the *Amazon Route 53 Developer Guide*.
