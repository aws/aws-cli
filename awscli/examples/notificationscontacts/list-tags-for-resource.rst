**To list the tags**

The following ``list-tags-for-resource`` example lists all the tags associated to the given resource ARN. ::

    aws notificationscontacts list-tags-for-resource \
        --arn arn:aws:notifications::123456789012:configuration/a01jjzhee9p37n8gc2ke1mr5zjx

Output::

    {
        "tags": {
            "name": "clidemo",
            "costcenter": "usernotifications"
        }
    }

For more information, see `Tagging your AWS User Notifications resources <https://docs.aws.amazon.com/notifications/latest/userguide/tagging-resources.html>`__ in the *AWS User Notifications User Guide*.