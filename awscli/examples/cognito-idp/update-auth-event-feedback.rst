**To update auth event feedback**

The following ``update-auth-event-feedback`` example updates authorization event feedback. It marks the event "Valid". ::

    aws cognito-idp update-auth-event-feedback \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com \
        --event-id EVENT_ID \
        --feedback-token FEEDBACK_TOKEN \
        --feedback-value "Valid"

This command produces no output.
