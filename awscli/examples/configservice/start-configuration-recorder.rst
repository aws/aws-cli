**To start the configuration recorder**

The following ``start-configuration-recorder`` example starts the default configuration recorder. ::

    aws configservice start-configuration-recorder \
        --configuration-recorder-name default

This command produces no output. To verify that AWS Config is recording your resources, run the `get-status`__ command.

.. __: http://docs.aws.amazon.com/cli/latest/reference/configservice/get-status.html
