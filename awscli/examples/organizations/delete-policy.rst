**To delete a policy**

The following ``delete-policy`` example deletes a policy from an organization. The example assumes that you previously detached the policy from all entities. This command produces no output. ::

    aws organizations delete-policy \
        --policy-id p-examplepolicyid111