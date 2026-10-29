**To delete a custom authorizer**

The following ``delete-authorizer`` example deletes the authorizer named ``CustomAuthorizer``. A custom authorizer must be in the ``INACTIVE`` state before you can delete it. ::

    aws iot delete-authorizer \
        --authorizer-name CustomAuthorizer

This command produces no output.

For more information, see `Creating and managing custom authorizers (CLI) <https://docs.aws.amazon.com/iot/latest/developerguide/config-custom-auth.html>`__ in the *AWS IoT Core Developer Guide*.
