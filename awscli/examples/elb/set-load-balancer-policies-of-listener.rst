**Example 1: To replace the policies associated with a listener**

The following ``set-load-balancer-policies-of-listener`` example replaces the policies that are currently associated with the specified listener. ::

    aws elb set-load-balancer-policies-of-listener \
        --load-balancer-name my-load-balancer \
        --load-balancer-port 443 \
        --policy-names my-SSLNegotiation-policy

This command produces no output.


**Example 2: To remove all policies associated with your listener**

The following ``set-load-balancer-policies-of-listener`` example removes all policies that are currently associated with the specified listener. ::

    aws elb set-load-balancer-policies-of-listener \
        --load-balancer-name my-load-balancer \
        --load-balancer-port 443 \
        --policy-names []

This command produces no output.

To confirm that the policies are removed from the load balancer, use the ``describe-load-balancer-policies`` command.

