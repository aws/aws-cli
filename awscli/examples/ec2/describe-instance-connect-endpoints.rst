**To describe an EC2 Instance Connect Endpoint**

The following ``describe-instance-connect-endpoints`` example describes the specified EC2 Instance Connect Endpoint. ::

    aws ec2 describe-instance-connect-endpoints \
        --instance-connect-endpoint-ids eice-0123456789example

Output::

    {
        "InstanceConnectEndpoints": [
            {
                "OwnerId": "123456789012",
                "InstanceConnectEndpointId": "eice-0123456789example",
                "InstanceConnectEndpointArn": "arn:aws:ec2:us-west-2:123456789012:instance-connect-endpoint/eice-0123456789example",
                "State": "create-complete",
                "StateMessage": "",
                "DnsName": "eice-0123456789example.b67b86ba.ec2-instance-connect-endpoint.us-west-2.amazonaws.com",
                "NetworkInterfaceIds": [
                    "eni-0123456789example"
                ],
                "VpcId": "vpc-0123abcd",
                "AvailabilityZone": "us-west-2d",
                "CreatedAt": "2023-02-07T12:05:37+00:00",
                "SubnetId": "subnet-0123abcd",
                "Tags": []
            }
        ]
    }

For more information, see `Create an EC2 Instance Connect Endpoint <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-ec2-instance-connect-endpoints.html>`__ in the *Amazon EC2 User Guide*.
