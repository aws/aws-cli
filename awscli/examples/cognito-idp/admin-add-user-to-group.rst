**To add a user to a group**

The following ``admin-add-user-to-group`` example adds user Jane to group MyGroup. ::

    aws cognito-idp admin-add-user-to-group \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username Jane \
        --group-name MyGroup

