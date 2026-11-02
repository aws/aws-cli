**To update the settings for your account**

The following ``update-account-settings`` example disables the remote control of shared screens for the specified Amazon Chime account. ::

    aws chime update-account-settings \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --account-settings DisableRemoteControl=true

This command produces no output.

For more information, see `Managing meeting settings <https://docs.aws.amazon.com/chime/latest/ag/mtg-settings.html>`__ in the *Amazon Chime Administration Guide*.
