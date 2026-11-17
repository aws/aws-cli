**Example 1: To create a license configuration**

The following ``create-license-configuration`` example creates a license configuration with a hard limit of 10 cores. ::

    aws license-manager create-license-configuration \
        --name my-license-configuration \
        --license-counting-type Core \
        --license-count 10 \
        --license-count-hard-limit

Output::

    {
        "LicenseConfigurationArn": "arn:aws:license-manager:us-west-2:123456789012:license-configuration:lic-6eb6586f508a786a2ba41EXAMPLE1111"
    }

For more information, see `Create a self-managed license in License Manager <https://docs.aws.amazon.com/license-manager/latest/userguide/create-license-configuration.html>`__ in the *AWS License Manager User Guide*.

**Example 2: To create a license configuration**

The following ``create-license-configuration`` example creates a license configuration with a soft limit of 100 vCPUs. It uses a rule to enable vCPU optimization. ::

    aws license-manager create-license-configuration \
        --name my-license-configuration \
        --license-counting-type vCPU \
        --license-count 100 \
        --license-rules "#honorVcpuOptimization=true"

Output::

    {
        "LicenseConfigurationArn": "arn:aws:license-manager:us-west-2:123456789012:license-configuration:lic-6eb6586f508a786a2ba41EXAMPLE2222"
    }

For more information, see `Create a self-managed license in License Manager <https://docs.aws.amazon.com/license-manager/latest/userguide/create-license-configuration.html>`__ in the *AWS License Manager User Guide*.
