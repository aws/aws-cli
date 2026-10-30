**To delete a Verified Access endpoint**

The following ``delete-verified-access-endpoint`` example deletes the specified Verified Access endpoint. ::

    aws ec2 delete-verified-access-endpoint \
        --verified-access-endpoint-id vae-066fac616d4d546f2

Output::

    {
        "VerifiedAccessEndpoint": {
            "VerifiedAccessInstanceId": "vai-0ce000c0b7643abea",
            "VerifiedAccessGroupId": "vagr-0dbe967baf14b7235",
            "VerifiedAccessEndpointId": "vae-066fac616d4d546f2",
            "ApplicationDomain": "example.com",
            "EndpointType": "network-interface",
            "AttachmentType": "vpc",
            "DomainCertificateArn": "arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "EndpointDomain": "my-ava-app.edge-00c3372d53b1540bb.vai-0ce000c0b7643abea.prod.verified-access.us-west-2.amazonaws.com",
            "SecurityGroupIds": [
                "sg-004915970c4c8f13a"
            ],
            "NetworkInterfaceOptions": {
                "NetworkInterfaceId": "eni-0aec70418c8d87a0f",
                "Protocol": "https",
                "Port": 443
            },
            "Status": {
                "Code": "deleting"
            },
            "Description": "Testing Verified Access",
            "CreationTime": "2023-08-25T20:54:43",
            "LastUpdatedTime": "2023-08-25T22:46:32"
        }
    }

For more information, see `Verified Access endpoints <https://docs.aws.amazon.com/verified-access/latest/ug/verified-access-endpoints.html>`__ in the *AWS Verified Access User Guide*.
