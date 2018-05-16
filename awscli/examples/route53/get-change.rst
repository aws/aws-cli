**To get information about a change-resource-record-sets request**

The following ``get-change`` command gets information about the ``change-resource-record-sets request`` with an ``Id`` of ``/change/CWPIK4URU2I5S``. The response includes the status of the request (PENDING or INSYNC), the comment in the request (if any), and the date and time (in UTC) that the request was submitted::

  aws route53 get-change --id /change/CWPIK4URU2I5S

