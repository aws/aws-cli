**To delete a source server**

The following ``delete-source-server`` example deletes the specified source server from the AWS Elastic Disaster Recovery service. The source server must be disconnected first. ::

    aws drs delete-source-server \
        --source-server-id s-1234567890abcdef0

This command produces no output.

For more information, see `Managing source servers <https://docs.aws.amazon.com/drs/latest/userguide/managing-source-servers.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
