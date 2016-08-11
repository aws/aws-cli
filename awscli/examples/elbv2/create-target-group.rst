**To create a target group**

This example creates a target group that you can use to route traffic to targets using HTTP on port 80. This target group uses the default health check configuration.

Command::

  aws elbv2 create-target-group --name my-targets --protocol HTTP --port 80 --vpc-id vpc-3ac0fb5f

Output::

  {
    "TargetGroups": [
        {
            "HealthCheckPath": "/",
            "HealthCheckIntervalSeconds": 30,
            "VpcId": "vpc-3ac0fb5f",
            "Protocol": "HTTP",
            "HealthCheckTimeoutSeconds": 5,
            "HealthCheckProtocol": "HTTP",
            "UnhealthyThresholdCount": 2,
            "HealthyThresholdCount": 5,
            "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
            "Matcher": {
                "HttpCode": "200"
            },
            "HealthCheckPort": "traffic-port",
            "Port": 80,
            "TargetGroupName": "my-targets"
        }
    ]
  }
