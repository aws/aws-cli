**To describe events**

The following ``describe-events`` command returns information about all events
that are associated with a Chef Automate server named ``automate-06``.::

  aws opsworks-cm describe-events --server-name 'automate-06'

The output for each event entry returned by the command resembles the following.
*Output*::

  {
   "ServerEvents": [ 
      { 
         "CreatedAt": 2016-07-29T13:38:47.520Z,
         "LogUrl": "https://s3.amazonaws.com/automate-06/automate-06-20160729133847520",
         "Message": "Updates successfully installed.",
         "ServerName": "automate-06"
      }
   ]
}

**More Information**

For more information, see `General Troubleshooting Tips`_ in the *AWS OpsWorks User Guide*.

.. _`General Troubleshooting Tips`: http://docs.aws.amazon.com/opsworks/latest/userguide/troubleshoot-opscm.html#d0e4561

