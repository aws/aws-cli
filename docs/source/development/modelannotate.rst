Model Customizations
====================

For every file ``<servicename>.json`` in the ``./services`` directory, a set of
customizations can be added to a ``<servicename>.extra.json`` file.  The format
of this file is documented here.

Annotating Operations
---------------------

Anything specified in the "operations" key of the extra json file will be
merged in with the "operations" key of the service model.  For example, suppose
we wanted to add a "foo" attribute to the "AssumeRole" operation in STS.  To do
so, we'd create a ``./services/sts.extra.json`` file::

    {
        "operations": {
            "AssumeRole": {
                "foo": "bar"
            }
        }
    }

This would then be merged in with the other keys in the "AssumeRole" dict.
