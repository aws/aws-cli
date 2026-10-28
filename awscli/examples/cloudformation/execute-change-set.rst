**To execute a change set**

The following ``execute-change-set`` example executes a change set specified by change set name and stack name. This command produces no output. ::

    aws cloudformation execute-change-set \
        --change-set-name my-change-set \
        --stack-name my-stack

The following ``execute-change-set`` example executes a change set specified by the full ARN of the change set. This command produces no output. ::

    aws cloudformation execute-change-set \
        --change-set-name arn:aws:cloudformation:us-west-2:123456789012:changeSet/my-change-set/bc9555ba-a949-xmpl-bfb8-f41d04ec5784
