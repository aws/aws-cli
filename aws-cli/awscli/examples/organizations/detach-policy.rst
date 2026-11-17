**To detach a policy from a root, OU, or account**

The following ``detach-policy`` example detaches a policy from an OU. ::

    aws organizations detach-policy \
        --target-id ou-examplerootid111-exampleouid111 \
        --policy-id p-examplepolicyid111

This command produces no output.

For more information, see `Detaching organization policies with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_policies_detach.html>`__ in the *AWS Organizations User Guide*.
