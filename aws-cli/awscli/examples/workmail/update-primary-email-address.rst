**To update a primary email address**

The following ``update-primary-email-address`` example updates the primary email address of the specified entity (user, group, or resource). ::

    aws workmail update-primary-email-address \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 \
        --entity-id S-1-1-11-1111111111-2222222222-3333333333-3333 \
        --email exampleUser2@site.awsapps.com

This command produces no output.

For more information, see `Editing user details <https://docs.aws.amazon.com/workmail/latest/adminguide/edit_user.html>`__ in the *Amazon WorkMail Administrator Guide*.
