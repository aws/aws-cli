**To remove a member from a resource**

The following ``disassociate-delegate-from-resource`` example removes the specified member from a resource. ::

    aws workmail disassociate-delegate-from-resource \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 \
        --resource-id r-68bf2d3b1c0244aab7264c24b9217443 \
        --entity-id S-1-1-11-1111111111-2222222222-3333333333-3333

This command produces no output.

For more information, see `Editing resource details <https://docs.aws.amazon.com/workmail/latest/adminguide/edit_resource.html>`__ in the *Amazon WorkMail Administrator Guide*.
