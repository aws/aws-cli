**To update the visibility or status of a problem in an application**

This example uses the ``update-problem`` command to update the status of a problem to resolved. ::

    aws application-insights update-problem \
        --problem-id p-11b78b15-6f5b-40ca-9da7-12d12345c68b \
        --update-status RESOLVED

This command returns to the prompt if successful.