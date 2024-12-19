**To update a component in an application**

This example uses the ``update-component`` command to update a component by changing its name and resource list. ::

    aws application-insights update-component \
        --resource-group-name MYEC2 \
        --component-name "custom" \
        --resource-list "arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56" \
        --new-component-name custom_new

This command returns to the prompt if successful.