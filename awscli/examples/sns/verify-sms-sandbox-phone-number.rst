**To verify a destination phone number with a one-time password (OTP)**

The following `verify-sms-sandbox-phone-number` example verifies the specified destination phone number using the OTP. ::

    aws sns verify-sms-sandbox-phone-number \
        --phone-number +1555550100 \
        --one-time-password 48291

This command produces no output.