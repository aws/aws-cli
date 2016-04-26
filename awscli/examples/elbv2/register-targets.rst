**To register targets with a target group**

This example registers the specified instances with the specified target group.

Command::

  aws elbv2 register-targets --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067 --targets Id=i-80c8dd94 Id=i-ceddcd4d 

**To register targets with a target group using port overrides**

This example registers the specified instance with the specified target group using multiple ports. This enables you to register ECS containers on the same instance as targets in the target group.

Command::

  aws elbv2 register-targets --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-internal-targets/3bb63f11dfb0faf9 --targets Id=i-80c8dd94,Port=80 Id=i-80c8dd94,Port=766
