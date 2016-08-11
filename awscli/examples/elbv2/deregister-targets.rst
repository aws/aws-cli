**To deregister a target from a target group**

This example deregisters the specified instance from the specified target group.

Command::

  aws elbv2 deregister-targets --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067 --targets Id=i-0f76fade
