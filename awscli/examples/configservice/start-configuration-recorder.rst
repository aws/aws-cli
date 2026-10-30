**To start the configuration recorder**

The following ``start-configuration-recorder`` example starts the default configuration recorder. ::

    aws configservice start-configuration-recorder \
        --configuration-recorder-name default

This command produces no output. To verify that AWS Config is recording your resources, run the `get-status`__ command.

.. __: https://docs.aws.amazon.com/cli/latest/reference/configservice/get-status.html

For more information, see `Working with the configuration recorder <https://docs.aws.amazon.com/config/latest/developerguide/stop-start-recorder.html>`__ in the *AWS Config Developer Guide*.
