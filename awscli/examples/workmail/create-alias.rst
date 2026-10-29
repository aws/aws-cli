**To create an alias**

The following ``create-alias`` example creates an alias for the specified entity (user or group). ::

    aws workmail create-alias \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 \
        --entity-id S-1-1-11-1122222222-2222233333-3333334444-4444 \
        --alias exampleAlias@site.awsapps.com

This command produces no output.

For more information, see `Managing group aliases <https://docs.aws.amazon.com/workmail/latest/adminguide/managing_groups.html>`__ in the *Amazon WorkMail Administrator Guide*.
