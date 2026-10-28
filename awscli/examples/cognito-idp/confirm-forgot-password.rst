**To confirm a forgotten password**

The following ``confirm-forgot-password`` example confirms a forgotten password for username diego@example.com. This command produces no output. ::

    aws cognito-idp confirm-forgot-password \
        --client-id 3n4b5urk1ft4fl3mg5e62d9ado \
        --username diego@example.com \
        --password PASSWORD \
        --confirmation-code CONF_CODE

