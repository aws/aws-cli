**Example 1: To attach a policy to an OU**

The following ``attach-policy`` example attaches a service control policy (SCP) to an OU. ::

    aws organizations attach-policy \
        --policy-id p-examplepolicyid111 \
        --target-id ou-examplerootid111-exampleouid111

For more information, see `Attaching organization policies with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_policies_attach.html>`__ in the *AWS Organizations User Guide*.

This command produces no output.

**Example 2: To attach a policy to an account**

The following ``attach-policy`` example attaches a service control policy directly to an account. ::

    aws organizations attach-policy \
        --policy-id p-examplepolicyid111 \
        --target-id 123456789222

This command produces no output.

For more information, see `Attaching organization policies with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_policies_attach.html>`__ in the *AWS Organizations User Guide*.
