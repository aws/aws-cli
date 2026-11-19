**To enable Amazon Macie**

The following ``enable-macie`` example enables Amazon Macie for the current AWS account and Region. ::

    aws macie2 enable-macie

Output::

    {
        "status": "ENABLED"
    }

**To enable Amazon Macie with custom configuration**

The following ``enable-macie`` example enables Amazon Macie with a custom finding publishing frequency and status. ::

    aws macie2 enable-macie \
        --finding-publishing-frequency FIFTEEN_MINUTES \
        --status PAUSED

Output::

    {
        "status": "PAUSED"
    }
