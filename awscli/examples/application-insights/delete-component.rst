**To delete a component from an application**

This example uses the ``delete-component`` command to ungroup a component from an application. ::

    aws application-insights delete-component \
        --resource-group-name MYEC2 \
        --component-name custom_new

This command returns to the prompt if successful.