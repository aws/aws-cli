**To delete a policy**

The following ``delete-policy`` example deletes a policy from an organization. The example assumes that you previously detached the policy from all entities. ::

    aws organizations delete-policy \
        --policy-id p-examplepolicyid111

This command produces no output.