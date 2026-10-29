**To create an EC2 Instance Connect Endpoint**

The following ``create-instance-connect-endpoint`` example creates an EC2 Instance Connect Endpoint in the specified subnet. ::

    aws ec2 create-instance-connect-endpoint \
        --subnet-id subnet-0123456789example

Output::

    {
        "InstanceConnectEndpoint": {
            "VpcId": "vpc-0123abcd",
            "InstanceConnectEndpointArn": "arn:aws:ec2:us-west-2:123456789012:instance-connect-endpoint/eice-0123456789example",
            "AvailabilityZone": "us-west-2a",
            "NetworkInterfaceIds": [
                "eni-0123abcd"
            ],
            "PreserveClientIp": true,
            "Tags": [],
            "FipsDnsName": "eice-0123456789example.0123abcd.fips.ec2-instance-connect-endpoint.us-west-2.amazonaws.com",
            "StateMessage": "",
            "State": "create-complete",
            "DnsName": "eice-0123456789example.0123abcd.ec2-instance-connect-endpoint.us-west-2.amazonaws.com",
            "SubnetId": "subnet-0123abcd",
            "OwnerId": "123456789012",
            "SecurityGroupIds": [
                "sg-0123abcd"
            ],
            "InstanceConnectEndpointId": "eice-0123456789example",
            "CreatedAt": "2023-04-07T15:43:53.000Z"
        }
    }

For more information, see `Create an EC2 Instance Connect Endpoint <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-ec2-instance-connect-endpoints.html>`__ in the *Amazon EC2 User Guide*.
