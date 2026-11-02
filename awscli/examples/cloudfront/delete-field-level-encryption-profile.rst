**To delete a CloudFront field-level encryption profile**

The following ``delete-field-level-encryption-profile`` example deletes the CloudFront field-level encryption profile
with the ID ``PPK0UOSIF5WSV``. To delete a field-level encryption profile, you
must have its ID and ``ETag``. The ID is returned in the output of the
`create-field-level-encryption-profile
<create-field-level-encryption-profile.html>`_ and
`list-field-level-encryption-profiles
<list-field-level-encryption-profiles.html>`_ commands.
To get the ``ETag``, use the
`get-field-level-encryption-profile
<get-field-level-encryption-profile.html>`_ or
`get-field-level-encryption-profile-config
<get-field-level-encryption-profile-config.html>`_ command.
Use the ``--if-match`` option to provide the profile's ``ETag``. ::

    aws cloudfront delete-field-level-encryption-profile \
        --id PPK0UOSIF5WSV \
        --if-match EJETYFJ9CL66D

This command produces no output.

When successful, this command has no output.

For more information, see `Use field-level encryption to help protect sensitive data <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/field-level-encryption.html>`__ in the *Amazon CloudFront Developer Guide*.
