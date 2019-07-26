**To create an empty core definition**

The following ``create-core-definition`` example creates an empty (no initial version) Greengrass core definition. Before the core is usable, you must use the ``create-core-definition-version`` command to provide the other parameters for the core. ::

    aws greengrass create-core-definition \
        --name cliGroup_Core

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/b5c08008-54cb-44bd-9eec-c121b04283b5",
        "CreationTimestamp": "2019-06-25T18:23:22.106Z",
        "Id": "b5c08008-54cb-44bd-9eec-c121b04283b5",
        "LastUpdatedTimestamp": "2019-06-25T18:23:22.106Z",
        "Name": "cliGroup_Core"
    }
