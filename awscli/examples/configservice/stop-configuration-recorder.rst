**To stop the configuration recorder**

The following ``stop-configuration-recorder`` example stops the default configuration recorder. ::

    aws configservice stop-configuration-recorder \
        --configuration-recorder-name default

This command produces no output. To verify that AWS Config is not recording your resources, run the `get-status`__ command.

.. __: https://docs.aws.amazon.com/cli/latest/reference/configservice/get-status.html

For more information, see `Working with the configuration recorder <https://docs.aws.amazon.com/config/latest/developerguide/stop-start-recorder.html>`__ in the *AWS Config Developer Guide*.
