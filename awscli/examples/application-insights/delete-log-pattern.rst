**To delete a log pattern from a log pattern set**

This example uses the ``delete-log-pattern`` command to remove a log pattern from a log pattern set. ::

    aws application-insights delete-log-pattern \
        --resource-group-name MYEC2 \
        --pattern-set-name MYTEST \
        --pattern-name MYPATTERN

This command returns to the prompt if successful.