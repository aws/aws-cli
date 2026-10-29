**To update a license configuration**

The following ``update-license-configuration`` example updates the specified license configuration to remove the hard limit. ::

    aws license-manager update-license-configuration \
        --no-license-count-hard-limit \
        --license-configuration-arn arn:aws:license-manager:us-west-2:123456789012:license-configuration:lic-6eb6586f508a786a2ba4f56c1EXAMPLE 

This command produces no output.

For more information, see `Edit a self-managed license in License Manager <https://docs.aws.amazon.com/license-manager/latest/userguide/modify-license-configuration.html>`__ in the *AWS License Manager User Guide*.

The following ``update-license-configuration`` example updates the specified license configuration to change its status to ``DISABLED``. ::

    aws license-manager update-license-configuration \
        --license-configuration-status DISABLED \
        --license-configuration-arn arn:aws:license-manager:us-west-2:123456789012:license-configuration:lic-6eb6586f508a786a2ba4f56c1EXAMPLE

This command produces no output.

For more information, see `Deactivate a self-managed license in License Manager <https://docs.aws.amazon.com/license-manager/latest/userguide/deactivate-license-configuration.html>`__ in the *AWS License Manager User Guide*.
