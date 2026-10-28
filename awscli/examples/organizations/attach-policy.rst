**Example 1: To attach a policy to an OU**

The following ``attach-policy`` example attaches a service control policy (SCP) to an OU. This command produces no output. ::

    aws organizations attach-policy \
        --policy-id p-examplepolicyid111 \
        --target-id ou-examplerootid111-exampleouid111

**Example 2: To attach a policy to an account**

The following ``attach-policy`` example attaches a service control policy directly to an account. This command produces no output. ::

    aws organizations attach-policy \
        --policy-id p-examplepolicyid111 \
        --target-id 333333333333
