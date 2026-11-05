**To delete a CloudFront distribution**

The following ``delete-distribution`` example deletes the CloudFront distribution with the ID
``EDFDVBD6EXAMPLE``. Before you can delete a distribution, you must disable it.
To disable a distribution, use the `update-distribution
<update-distribution.html>`_ command. For more information, see the
`update-distribution examples <update-distribution.html#examples>`_.

When a distribution is disabled, you can delete it. To delete a distribution,
you must use the ``--if-match`` option to provide the distribution's ``ETag``.
To get the ``ETag``, use the `get-distribution <get-distribution.html>`_ or
`get-distribution-config <get-distribution-config.html>`_ command. ::

    aws cloudfront delete-distribution \
        --id EDFDVBD6EXAMPLE \
        --if-match E2QWRUHEXAMPLE

This command produces no output.

When successful, this command has no output.

For more information, see `Delete a distribution <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowToDeleteDistribution.html>`__ in the *Amazon CloudFront Developer Guide*.
