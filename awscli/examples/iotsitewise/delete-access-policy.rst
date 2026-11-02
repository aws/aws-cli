**To revoke a user's access to a project or portal**

The following ``delete-access-policy`` example deletes an access policy that grants a user administrative access to a portal. ::

    aws iotsitewise delete-access-policy \
        --access-policy-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Adding or removing portal administrators <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/portal-change-admins.html>`__ in the *AWS IoT SiteWise User Guide*.