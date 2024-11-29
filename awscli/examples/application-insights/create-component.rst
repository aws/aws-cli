**To create a component for an application**

This example uses the ``create-component command`` to create a component by grouping similar standalone instances to monitor.

    aws application-insights create-component \
        --resource-group-name MYEC2 \
        --component-name mycustomcomp \
        --resource-list arn:aws:ec2:eu-west-1:123456789012:instance/i-0f6bcd63ce2f03f

This command returns to the prompt if successful