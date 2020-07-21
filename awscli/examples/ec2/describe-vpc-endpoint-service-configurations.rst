**To describe endpoint service configurations**

This example describes your endpoint service configurations.

Command::

  aws ec2 describe-vpc-endpoint-service-configurations

Output::

 {
    "ServiceConfigurations": [
        {
            "ServiceType": [
                {
                    "ServiceType": "Interface"
                }
            ], 
            "NetworkLoadBalancerArns": [
                "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/NLBforService/8218753950b25648"
            ], 
            "ServiceName": "com.amazonaws.vpce.us-east-1.vpce-svc-0e7555fb6441987e1", 
            "ServiceState": "Available", 
            "ServiceId": "vpce-svc-0e7555fb6441987e1", 
            "AcceptanceRequired": true, 
            "AvailabilityZones": [
                "us-east-1d"
            ], 
            "BaseEndpointDnsNames": [
                "vpce-svc-0e7555fb6441987e1.us-east-1.vpce.amazonaws.com"
            ]
        }
    ]
 }