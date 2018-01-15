**To create an endpoint service configuration**

This example creates a VPC endpoint service configuration using the load balancer ``nlb-vpce``. This example also specifies that requests to connect to the service through an interface endpoint must be accepted.

Command::

  aws ec2 create-vpc-endpoint-service-configuration --network-load-balancer-arns arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/nlb-vpce/e94221227f1ba532 --acceptance-required

Output::

 {
    "ServiceConfiguration": {
        "ServiceType": [
            {
                "ServiceType": "Interface"
            }
        ], 
        "NetworkLoadBalancerArns": [
            "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/nlb-vpce/e94221227f1ba532"
        ], 
        "ServiceName": "com.amazonaws.vpce.us-east-1.vpce-svc-03d5ebb7d9579a2b3", 
        "ServiceState": "Available", 
        "ServiceId": "vpce-svc-03d5ebb7d9579a2b3", 
        "AcceptanceRequired": true, 
        "AvailabilityZones": [
            "us-east-1d"
        ], 
        "BaseEndpointDnsNames": [
            "vpce-svc-03d5ebb7d9579a2b3.us-east-1.vpce.amazonaws.com"
        ]
    }
 }