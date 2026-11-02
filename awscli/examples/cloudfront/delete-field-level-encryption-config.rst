**To delete a CloudFront field-level encryption configuration**

The following ``delete-field-level-encryption-config`` example deletes the CloudFront field-level encryption
configuration with the ID ``C3KM2WVD605UAY``. To delete a field-level
encryption configuration, you must have its ID and ``ETag``. The ID is returned
in the output of the
`create-field-level-encryption-config
<create-field-level-encryption-config.html>`_ and
`list-field-level-encryption-configs
<list-field-level-encryption-configs.html>`_ commands.
To get the ``ETag``, use the
`get-field-level-encryption
<get-field-level-encryption.html>`_ or
`get-field-level-encryption-config
<get-field-level-encryption-config.html>`_ command.
Use the ``--if-match`` option to provide the configuration's ``ETag``. ::

    aws cloudfront delete-field-level-encryption-config \
        --id C3KM2WVD605UAY \
        --if-match E26M4BIAV81ZF6

This command produces no output.

When successful, this command has no output.

For more information, see `Use field-level encryption to help protect sensitive data <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/field-level-encryption.html>`__ in the *Amazon CloudFront Developer Guide*.
