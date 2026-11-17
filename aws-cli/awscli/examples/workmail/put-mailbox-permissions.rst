**To set mailbox permissions**

The following ``put-mailbox-permissions`` example sets full access permissions for the specified grantee (user or group). The entity represents the owner of the mailbox. ::

    aws workmail put-mailbox-permissions \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 \
        --entity-id S-1-1-11-1111111111-2222222222-3333333333-3333 \
        --grantee-id S-1-1-11-1122222222-2222233333-3333334444-4444 \
        --permission-values FULL_ACCESS

This command produces no output.

For more information, see `Managing mailbox permissions for users <https://docs.aws.amazon.com/workmail/latest/adminguide/enable_mail_perms.html>`__ in the *Amazon WorkMail Administrator Guide*.
