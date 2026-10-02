**To delete a launch action from a source server**

The following ``delete-launch-action`` example removes the specified post-launch action from a source server. ::

    aws drs delete-launch-action \
        --resource-id s-1234567890abcdef0 \
        --action-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Post-launch actions <https://docs.aws.amazon.com/drs/latest/userguide/post-launch-actions.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
