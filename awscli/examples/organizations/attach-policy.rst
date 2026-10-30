**Example 1: To attach a policy to an OU**

The following ``attach-policy`` example attaches a service control policy (SCP) to an OU. ::

    aws organizations attach-policy \
        --policy-id p-examplepolicyid111 \
        --target-id ou-examplerootid111-exampleouid111

This command produces no output.

**Example 2: To attach a policy to an account**

The following ``attach-policy`` example attaches a service control policy directly to an account. ::

    aws organizations attach-policy \
        --policy-id p-examplepolicyid111 \
        --target-id 333333333333

This command produces no output.
