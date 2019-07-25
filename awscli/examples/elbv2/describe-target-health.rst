**To describe the health of the targets for a target group**

This example describes the health of the targets for the specified target group. These targets are healthy.

Command::

  aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067

Output::

  {
    "TargetHealthDescriptions": [
        {
            "HealthCheckPort": "80",
            "Target": {
                "Id": "i-ceddcd4d",
                "Port": 80
            },
            "TargetHealth": {
                "State": "healthy"
            }
        },
        {
            "HealthCheckPort": "80",
            "Target": {
                "Id": "i-0f76fade",
                "Port": 80
            },
            "TargetHealth": {
                "State": "healthy"
            }
        }
    ]
  }

**To describe the health of a target**

This example describes the health of the specified target. This target is healthy.

Command::

  aws elbv2 describe-target-health --targets Id=i-0f76fade,Port=80 --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067

Output::

  {
    "TargetHealthDescriptions": [
        {
            "HealthCheckPort": "80",
            "Target": {
                "Id": "i-0f76fade",
                "Port": 80
            },
            "TargetHealth": {
                "State": "healthy"
            }
        }
    ]
  }

The following is an example response for a target whose target group is not specified in an action for a listener. This target can't receive traffic from the load balancer.

Output::

  {
    "TargetHealthDescriptions": [
        {
            "Target": {
                "Id": "i-0f76fade",
                "Port": 80
            },
            "TargetHealth": {
                "State": "unused",
                "Reason": "Target.NotInUse",
                "Description": "Given target group is not configured to receive traffic from ELB"
            }
        }
    ]
  }

The following is an example response for a target who target group was just specified in an action for a listener. The target is still being registered.

Output::

  {
    "TargetHealthDescriptions": [
        {
            "Target": {
                "Id": "i-0f76fade",
                "Port": 80
            },
            "TargetHealth": {
                "State": "initial",
                "Reason": "Elb.RegistrationInProgress",
                "Description": "Target registration is in progress"
            }
        }
    ]
  }

The following is an example response for an unhealthy target.

Output::

  {
    "TargetHealthDescriptions": [
        {
            "Target": {
                "Id": "i-0f76fade",
                "Port": 80
            },
            "TargetHealth": {
                "State": "unhealthy",
                "Reason": "Target.Timeout",
                "Description": "Connection to target timed out"
            }
        }
    ]
  }
