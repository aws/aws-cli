**To delete a CloudFront public key**

The following ``delete-public-key`` example deletes the CloudFront public key with the ID
``KDFB19YGCR002``. To delete a public key, you must have its ID and ``ETag``.
The ID is returned in the output of the
`create-public-key
<create-public-key.html>`_ and
`list-public-keys
<list-public-keys.html>`_ commands.
To get the ``ETag``, use the
`get-public-key
<get-public-key.html>`_ or
`get-public-key-config
<get-public-key-config.html>`_ command.
Use the ``--if-match`` option to provide the public key's ``ETag``. ::

    aws cloudfront delete-public-key \
        --id KDFB19YGCR002 \
        --if-match E2QWRUHEXAMPLE

This command produces no output.

When successful, this command has no output.

For more information, see `Use field-level encryption to help protect sensitive data <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/field-level-encryption.html>`__ in the *Amazon CloudFront Developer Guide*.
