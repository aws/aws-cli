**To deregister a target from a target group**

This example deregisters the specified instance from the specified target group.

Command::

  aws elbv2 deregister-targets --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067 --targets Id=i-0f76fade

**To deregister a target registered using port overrides**

This example deregisters an instance that was registered using port overrides.

Command::

  aws elbv2 deregister-targets --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-internal-targets/3bb63f11dfb0faf9 --targets Id=i-80c8dd94,Port=80 Id=i-80c8dd94,Port=766
