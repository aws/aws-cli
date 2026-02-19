**To verify an SMS sandbox destination phone number**

The following ``verify-sms-sandbox-phone-number`` example verifies a destination phone number in your SMS sandbox using the one-time password (OTP) received by SMS. ::

    aws sns verify-sms-sandbox-phone-number \
        --phone-number "+12065550100" \
        --one-time-password 123456

This command produces no output.
