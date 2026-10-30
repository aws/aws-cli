**Example 1: To replace the policies associated with a port for a backend instance**

The following ``set-load-balancer-policies-for-backend-server`` example replaces the policies that are currently associated with the specified port. ::

    aws elb set-load-balancer-policies-for-backend-server \
        --load-balancer-name my-load-balancer \
        --instance-port 80 \
        --policy-names my-ProxyProtocol-policy

This command produces no output.

For more information, see `Configure proxy protocol for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/enable-proxy-protocol.html>`__ in the *Classic Load Balancers Guide*.


**Example 2: To remove all policies that are currently associated with a port on your backend instance**

The following ``set-load-balancer-policies-for-backend-server`` example removes all policies associated with the specified port. ::

    aws elb set-load-balancer-policies-for-backend-server \
        --load-balancer-name my-load-balancer \
        --instance-port 80 \
        --policy-names []

This command produces no output.


To confirm that the policies are removed, use the ``describe-load-balancer-policies`` command.

For more information, see `Configure proxy protocol for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/enable-proxy-protocol.html>`__ in the *Classic Load Balancers Guide*.
