**To pause running until a registered target is in service**

The following ``wait target-in-service`` example pauses and resumes running only after it confirms that the specified target is in service. ::

    aws elbv2 wait target-in-service \
        --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067 \
        --targets Id=i-1234567890abcdef0,Port=80

This command produces no output.

For more information, see `Health checks for Application Load Balancer target groups <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html>`__ in the *Application Load Balancers User Guide*.
