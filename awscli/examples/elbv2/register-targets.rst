**Example 1: To register targets with a target group by instance ID**

The following ``register-targets`` example registers the specified instances with a target group. The target group must have a target type of ``instance``. ::

    aws elbv2 register-targets \
        --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067 \
        --targets Id=i-1234567890abcdef0 Id=i-0abcdef1234567890 

This command produces no output.

For more information, see `Register targets with your Application Load Balancer target group <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-register-targets.html>`__ in the *Application Load Balancers Guide*.

**Example 2: To register targets with a target group using port overrides**

The following ``register-targets`` example registers the specified instance with a target group using multiple ports. This enables you to register containers on the same instance as targets in the target group. ::

    aws elbv2 register-targets \
        --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-internal-targets/3bb63f11dfb0faf9 \
        --targets Id=i-0598c7d356eba48d7,Port=80 Id=i-0598c7d356eba48d7,Port=766

This command produces no output.

For more information, see `Register targets with your Application Load Balancer target group <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-register-targets.html>`__ in the *Application Load Balancers Guide*.

**Example 3: To register targets with a target group by IP address**

The following ``register-targets`` example registers the specified IP addresses with a target group. The target group must have a target type of ``ip``. ::

    aws elbv2 register-targets \
        --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-tcp-ip-targets/8518e899d173178f \
        --targets Id=10.0.1.15 Id=10.0.1.23

This command produces no output.

For more information, see `Register targets for your Network Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/network/target-group-register-targets.html>`__ in the *Network Load Balancers Guide*.

**Example 4: To register a Lambda function as a target**

The following ``register-targets`` example registers the specified IP addresses with a target group. The target group must have a target type of ``lambda``. You must grant Elastic Load Balancing permission to invoke the Lambda function. ::

    aws elbv2 register-targets \
        --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-tcp-ip-targets/8518e899d173178f \
        --targets Id=arn:aws:lambda:us-west-2:123456789012:function:my-function

This command produces no output.

For more information, see `Use Lambda functions as targets of an Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html>`__ in the *Application Load Balancers Guide*.
