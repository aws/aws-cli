**To delete a policy from your load balancer**

The following ``delete-load-balancer-policy`` example deletes the specified policy from the specified load balancer. The policy must not be enabled on any listener. This command produces no output. ::

    aws elb delete-load-balancer-policy \
        --load-balancer-name my-load-balancer \
        --policy-name my-duration-cookie-policy

