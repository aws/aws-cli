**To attach a certificate to your thing**

The following ``attach-thing-principal`` example attaches the specified principal in the form of a certificate to a thing named ``MyLightBulb``. ::

    aws iot attach-thing-principal \
        --thing-name "MyLightBulb" \
        --principal "arn:aws:iot:us-west-2:123456789012:cert/604c48437a57b7d5fc5d137c5be75011c6ee67c9a6943683a1acb4b1626bac36"

This command produces no output.

For more information, see `How to Manage Things with the Registry <https://docs.aws.amazon.com/iot/latest/developerguide/thing-registry.html>`__ in the *AWS IoT Developers Guide*.
