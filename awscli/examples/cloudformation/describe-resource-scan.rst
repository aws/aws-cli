**To describe a resource scan**

The following ``describe-resource-scan`` example describes the resource scan with the specified scan ID. ::

    aws cloudformation describe-resource-scan --region \
        --resource-scan-id arn:aws:cloudformation:us-east-1:123456789012:resourceScan/0a699f15-489c-43ca-a3ef-3e6ecfa5da60

Output::

    {
        "ResourceScanId": "arn:aws:cloudformation:us-east-1:123456789012:resourceScan/0a699f15-489c-43ca-a3ef-3e6ecfa5da60",
        "Status": "COMPLETE",
        "StartTime": "2025-08-21T03:10:38.485000+00:00",
        "EndTime": "2025-08-21T03:20:28.485000+00:00",
        "PercentageCompleted": 100.0,
        "ResourceTypes": [
            "AWS::CloudFront::CachePolicy",
            "AWS::CloudFront::OriginRequestPolicy",
            "AWS::EC2::DHCPOptions",
            "AWS::EC2::InternetGateway",
            "AWS::EC2::KeyPair",
            "AWS::EC2::NetworkAcl",
            "AWS::EC2::NetworkInsightsPath",
            "AWS::EC2::NetworkInterface",
            "AWS::EC2::PlacementGroup",
            "AWS::EC2::Route",
            "AWS::EC2::RouteTable",
            "AWS::EC2::SecurityGroup",
            "AWS::EC2::Subnet",
            "AWS::EC2::SubnetCidrBlock",
            "AWS::EC2::SubnetNetworkAclAssociation",
            "AWS::EC2::SubnetRouteTableAssociation",
            ...
        ],
        "ResourcesRead": 676
    }

For more information, see `Generating templates from existing resources <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/generate-IaC.html>`__ in the *AWS CloudFormation User Guide*.
