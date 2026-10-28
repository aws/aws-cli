**To stop the configuration recorder**

The following ``stop-configuration-recorder`` example stops the default configuration recorder. ::

    aws configservice stop-configuration-recorder \
        --configuration-recorder-name default

This command produces no output. To verify that AWS Config is not recording your resources, run the `get-status`__ command.

.. __: http://docs.aws.amazon.com/cli/latest/reference/configservice/get-status.html