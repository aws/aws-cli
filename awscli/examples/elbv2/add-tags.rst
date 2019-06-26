**To add tags to a load balancer**

This example adds the specified tags to the specified load balancer.

Command::

  aws elbv2 add-tags --resource-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188 --tags "Key=project,Value=lima" "Key=department,Value=digital-media"
