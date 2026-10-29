**Example 1: To enable deletion protection**

The following ``modify-load-balancer-attributes`` example enables deletion protection for the specified load balancer. ::

    aws elbv2 modify-load-balancer-attributes \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188 \
        --attributes Key=deletion_protection.enabled,Value=true

Output::

    {
        "Attributes": [
            {
                "Value": "true",
                "Key": "deletion_protection.enabled"
            },
            {
                "Value": "false",
                "Key": "access_logs.s3.enabled"
            },
            {
                "Value": "60",
                "Key": "idle_timeout.timeout_seconds"
            },
            {
                "Value": "",
                "Key": "access_logs.s3.prefix"
            },
            {
                "Value": "",
                "Key": "access_logs.s3.bucket"
            }
        ]
    }

For more information, see `Edit attributes for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-load-balancer-attributes.html#deletion-protection>`__ in the *Application Load Balancers Guide*.

**Example 2: To change the idle timeout**

The following ``modify-load-balancer-attributes`` example changes the idle timeout value for the specified load balancer. ::

    aws elbv2 modify-load-balancer-attributes \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188 \
        --attributes Key=idle_timeout.timeout_seconds,Value=30

Output::

    {
        "Attributes": [
            {
                "Value": "30",
                "Key": "idle_timeout.timeout_seconds"
            },
            {
                "Value": "false",
                "Key": "access_logs.s3.enabled"
            },
            {
                "Value": "",
                "Key": "access_logs.s3.prefix"
            },
            {
                "Value": "true",
                "Key": "deletion_protection.enabled"
            },
            {
                "Value": "",
                "Key": "access_logs.s3.bucket"
            }
        ]
    }

For more information, see `Edit attributes for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-load-balancer-attributes.html#connection-idle-timeout>`__ in the *Application Load Balancers Guide*.

**Example 3: To enable access logs**

The following ``modify-load-balancer-attributes`` example enables access logs for the specified load balancer. Note that the S3 bucket must exist in the same region as the load balancer and must have a policy attached that grants access to the Elastic Load Balancing service. ::

    aws elbv2 modify-load-balancer-attributes \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188 \
        --attributes Key=access_logs.s3.enabled,Value=true Key=access_logs.s3.bucket,Value=my-loadbalancer-logs Key=access_logs.s3.prefix,Value=myapp

Output::

    {
        "Attributes": [
            {
                "Value": "true",
                "Key": "access_logs.s3.enabled"
            },
            {
                "Value": "my-load-balancer-logs",
                "Key": "access_logs.s3.bucket"
            },
            {
                "Value": "myapp",
                "Key": "access_logs.s3.prefix"
            },
            {
                "Value": "60",
                "Key": "idle_timeout.timeout_seconds"
            },
            {
                "Value": "false",
                "Key": "deletion_protection.enabled"
            }
        ]
    }

For more information, see `Access logs for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html>`__ in the *Application Load Balancers Guide*.
