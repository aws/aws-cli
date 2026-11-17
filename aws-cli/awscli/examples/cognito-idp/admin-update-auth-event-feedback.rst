**To provide feedback for an authorization event**

The following ``admin-update-auth-event-feedback`` example sets the feedback value for an authorization event identified by event-id to Valid. ::

    aws cognito-idp admin-update-auth-event-feedback \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com \
        --event-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --feedback-value Valid

This command produces no output.

For more information, see `Working with adaptive authentication <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pool-settings-adaptive-authentication.html>`__ in the *Amazon Cognito Developer Guide*.
