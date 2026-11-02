**To delete a listener**

The following ``delete-listener`` example deletes the specified listener. ::

    aws elbv2 delete-listener \
        --listener-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2

This command produces no output.

For more information, see `Delete a listener for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/delete-listener.html>`__ in the *Application Load Balancers Guide*.
