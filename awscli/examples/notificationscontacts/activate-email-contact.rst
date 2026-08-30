**To activate an email contact**

The following ``activate-email-contact`` example activates an email contact using an activation code ``welf20z``. Activation code is made of alpha-numeric with 7 characters long and can be found in the email activation link as a token value::

    aws notificationscontacts activate-email-contact \
        --arn arn:aws:notifications-contacts::123456789012:emailcontact/a01jjz84gswr5vvvc0ep0s8r7qr \
        --code welf20z

This command produces no output.