**To describe VPC endpoint services**

This example describes all available endpoint services for the region.

Command::

  aws ec2 describe-vpc-endpoint-services

Output::

  {
    "ServiceDetails": [
        {
            "ServiceType": [
                {
                    "ServiceType": "Gateway"
                }
            ], 
            "AcceptanceRequired": false, 
            "ServiceName": "com.amazonaws.us-east-1.dynamodb", 
            "VpcEndpointPolicySupported": true, 
            "Owner": "amazon", 
            "AvailabilityZones": [
                "us-east-1a", 
                "us-east-1b", 
                "us-east-1c", 
                "us-east-1d", 
                "us-east-1e", 
                "us-east-1f"
            ], 
            "BaseEndpointDnsNames": [
                "dynamodb.us-east-1.amazonaws.com"
            ]
        }, 
        {
            "ServiceType": [
                {
                    "ServiceType": "Interface"
                }
            ], 
            "PrivateDnsName": "ec2.us-east-1.amazonaws.com", 
            "ServiceName": "com.amazonaws.us-east-1.ec2", 
            "VpcEndpointPolicySupported": false, 
            "Owner": "amazon", 
            "AvailabilityZones": [
                "us-east-1a", 
                "us-east-1b", 
                "us-east-1c", 
                "us-east-1d", 
                "us-east-1e", 
                "us-east-1f"
            ], 
            "AcceptanceRequired": false, 
            "BaseEndpointDnsNames": [
                "ec2.us-east-1.vpce.amazonaws.com"
            ]
        }, 
        {
            "ServiceType": [
                {
                    "ServiceType": "Interface"
                }
            ], 
            "PrivateDnsName": "ec2messages.us-east-1.amazonaws.com", 
            "ServiceName": "com.amazonaws.us-east-1.ec2messages", 
            "VpcEndpointPolicySupported": false, 
            "Owner": "amazon", 
            "AvailabilityZones": [
                "us-east-1a", 
                "us-east-1b", 
                "us-east-1c", 
                "us-east-1d", 
                "us-east-1e", 
                "us-east-1f"
            ], 
            "AcceptanceRequired": false, 
            "BaseEndpointDnsNames": [
                "ec2messages.us-east-1.vpce.amazonaws.com"
            ]
        }, 
        {
            "ServiceType": [
                {
                    "ServiceType": "Interface"
                }
            ], 
            "PrivateDnsName": "elasticloadbalancing.us-east-1.amazonaws.com", 
            "ServiceName": "com.amazonaws.us-east-1.elasticloadbalancing", 
            "VpcEndpointPolicySupported": false, 
            "Owner": "amazon", 
            "AvailabilityZones": [
                "us-east-1a", 
                "us-east-1b", 
                "us-east-1c", 
                "us-east-1d", 
                "us-east-1e", 
                "us-east-1f"
            ], 
            "AcceptanceRequired": false, 
            "BaseEndpointDnsNames": [
                "elasticloadbalancing.us-east-1.vpce.amazonaws.com"
            ]
        },
        {
            "ServiceType": [
                {
                    "ServiceType": "Interface"
                }
            ], 
            "PrivateDnsName": "kinesis.us-east-1.amazonaws.com", 
            "ServiceName": "com.amazonaws.us-east-1.kinesis-streams", 
            "VpcEndpointPolicySupported": false, 
            "Owner": "amazon", 
            "AvailabilityZones": [
                "us-east-1a", 
                "us-east-1b", 
                "us-east-1c", 
                "us-east-1d", 
                "us-east-1e", 
                "us-east-1f"
            ], 
            "AcceptanceRequired": false, 
            "BaseEndpointDnsNames": [
                "kinesis.us-east-1.vpce.amazonaws.com"
            ]
        }, 
        {
            "ServiceType": [
                {
                    "ServiceType": "Gateway"
                }
            ], 
            "AcceptanceRequired": false, 
            "ServiceName": "com.amazonaws.us-east-1.s3", 
            "VpcEndpointPolicySupported": true, 
            "Owner": "amazon", 
            "AvailabilityZones": [
                "us-east-1a", 
                "us-east-1b", 
                "us-east-1c", 
                "us-east-1d", 
                "us-east-1e", 
                "us-east-1f"
            ], 
            "BaseEndpointDnsNames": [
                "s3.us-east-1.amazonaws.com"
            ]
        }, 
        {
            "ServiceType": [
                {
                    "ServiceType": "Interface"
                }
            ], 
            "PrivateDnsName": "ssm.us-east-1.amazonaws.com", 
            "ServiceName": "com.amazonaws.us-east-1.ssm", 
            "VpcEndpointPolicySupported": true, 
            "Owner": "amazon", 
            "AvailabilityZones": [
                "us-east-1a", 
                "us-east-1b", 
                "us-east-1c", 
                "us-east-1d", 
                "us-east-1e"
            ], 
            "AcceptanceRequired": false, 
            "BaseEndpointDnsNames": [
                "ssm.us-east-1.vpce.amazonaws.com"
            ]
        }
    ], 
    "ServiceNames": [
        "com.amazonaws.us-east-1.dynamodb", 
        "com.amazonaws.us-east-1.ec2", 
        "com.amazonaws.us-east-1.ec2messages", 
        "com.amazonaws.us-east-1.elasticloadbalancing", 
        "com.amazonaws.us-east-1.kinesis-streams", 
        "com.amazonaws.us-east-1.s3", 
        "com.amazonaws.us-east-1.ssm"
    ]
  }