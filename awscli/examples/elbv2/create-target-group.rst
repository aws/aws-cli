**To create a target group for an Application Load Balancer**

This example creates a target group that you can use to route traffic to targets using HTTP on port 80. This target group uses the default health check configuration for an HTTP or HTTPS target group.

Command::

  aws elbv2 create-target-group --name my-targets --protocol HTTP --port 80 --vpc-id vpc-3ac0fb5f

Output::

  {
    "TargetGroups": [
        {
            "TargetGroupName": "my-targets",
            "Protocol": "HTTP",
            "Port": 80,
            "VpcId": "vpc-3ac0fb5f",
            "TargetType": "instance",
            "HealthyThresholdCount": 5,
            "Matcher": {
                "HttpCode": "200"
            },
            "UnhealthyThresholdCount": 2,
            "HealthCheckPath": "/",
            "HealthCheckProtocol": "HTTP",
            "HealthCheckPort": "traffic-port",
            "HealthCheckIntervalSeconds": 30,
            "HealthCheckTimeoutSeconds": 5,
            "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067"
        }
    ]
  }

By default, targets are registered by instance ID. To register targets by IP address, create a target group with a target type of ``ip``.

Command::

  aws elbv2 create-target-group --name my-ip-targets --protocol HTTP --port 80 --target-type ip --vpc-id vpc-3ac0fb5f

**To create a target group for a Network Load Balancer**

This example creates a target group that you can use to route traffic to targets using TCP on port 80. This target group uses the default health check configuration for a TCP target group.

Command::

  aws elbv2 create-target-group --name my-tcp-targets --protocol TCP --port 80 --vpc-id vpc-3ac0fb5f

Output::

  {
    "TargetGroups": [
        {
            "TargetGroupName": "my-tcp-targets",
            "Protocol": "TCP",
            "Port": 80,
            "VpcId": "vpc-3ac0fb5f",
            "TargetType": "instance",
            "HealthyThresholdCount": 3,
            "Matcher": {},
            "UnhealthyThresholdCount": 3,
            "HealthCheckProtocol": "TCP",
            "HealthCheckPort": "traffic-port",
            "HealthCheckIntervalSeconds": 30,
            "HealthCheckTimeoutSeconds": 10,
            "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-tcp-targets/b6bba954d1361c78"
        }
    ]
  }

By default, targets are registered by instance ID. To register targets by IP address, create a target group with a target type of ``ip``.

Command::

  aws elbv2 create-target-group --name my-tcp-ip-targets --protocol TCP --port 80 --target-type ip --vpc-id vpc-3ac0fb5f
