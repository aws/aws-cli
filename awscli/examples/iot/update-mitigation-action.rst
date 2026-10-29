**To update a mitigation action**

The following ``update-mitigation-action`` example updates the specified mitigation action named ``AddThingsToQuarantineGroupAction``, changes the thing group name, and sets ``overrideDynamicGroups`` to ``false``. You can verify your changes by using the ``describe-mitigation-action`` command. ::

    aws iot update-mitigation-action \
        --cli-input-json "{ \"actionName\": \"AddThingsToQuarantineGroupAction\", \"actionParams\": { \"addThingsToThingGroupParams\": {\"thingGroupNames\":[\"QuarantineGroup2\"],\"overrideDynamicGroups\": false}}}"

Output::

    {
        "actionArn": "arn:aws:iot:us-west-2:123456789012:mitigationaction/AddThingsToQuarantineGroupAction",
        "actionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `UpdateMitigationAction (Mitigation Action Commands) <https://docs.aws.amazon.com/iot/latest/developerguide/mitigation-action-commands.html>`__ in the *AWS IoT Developer Guide*.
