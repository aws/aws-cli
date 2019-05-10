**To pause script operations until a deployment is flagged as successful**

The following ``wait deployment-successful`` example pauses until the specified deployment completes successfully. ::

    aws deploy wait deployment-successful

This command produces no output, but pauses operation until the condition is met. It generates an error if the condition is not met after 120 checks that are 15 seconds apart.
