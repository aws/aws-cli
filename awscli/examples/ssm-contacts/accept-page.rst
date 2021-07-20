**To accept a page during and engagement**

The following ``accept-page`` using an accept code sent to the contact channel to accept a page. ::

    aws ssm-contacts accept-page \
        --page-id "arn:aws:ssm-contacts:us-east-2:682428703967:page/akuam/94ea0c7b-56d9-46c3-b84a-a37c8b067ad3" \
        --accept-type READ \
        --accept-code 425440 

Output::

    {
        "All of the output": "goes here",
        "More Output": [
            { "arrayitem1": 1 },
            { "arrayitem2": 2 }
        ]
        "Each indent": "Must be 4 spaces"
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.