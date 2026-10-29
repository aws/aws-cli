**To register an existing or disabled entity**

The following ``register-to-work-mail`` example enables the specified existing entity (user, group, or resource) to use Amazon WorkMail. ::

    aws workmail register-to-work-mail \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 \
        --entity-id S-1-1-11-1122222222-2222233333-3333334444-4444 \
        --email exampleGroup1@site.awsapps.com

This command produces no output.

For more information, see `Enabling groups <https://docs.aws.amazon.com/workmail/latest/adminguide/enable_existing_group.html>`__ in the *Amazon WorkMail Administrator Guide*.
