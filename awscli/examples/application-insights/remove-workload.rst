**To remove a workload from a component**

This example uses the ``remove-workload`` command to remove a workload from a component. ::

    aws application-insights remove-workload \
        --resource-group-name MYEC2 \
        --component-name arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56 \
        --workload-id w-1e2d0be3-fa45-6a78-b9d1-b2034d5dd67e

This command returns to the prompt if successful.