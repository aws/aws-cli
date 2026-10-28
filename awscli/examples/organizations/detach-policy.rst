**To detach a policy from a root, OU, or account**

The following ``detach-policy`` example detaches a policy from an OU. ::

    aws organizations detach-policy \
        --target-id ou-examplerootid111-exampleouid111 \
        --policy-id p-examplepolicyid111
