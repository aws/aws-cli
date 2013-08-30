Listing your Domains
--------------------

To list the SWF domains that you have registered for your account, you can use ``swf list-domains``. There is only one
required parameter: ``--registration-status``, which you can set to either ``REGISTERED`` or ``DEPRECATED``.

Here's a typical example::

    aws swf list-domains --registration-status REGISTERED

Result::

    {
      "domainInfos": [
        {
          "status": "REGISTERED",
          "name": "DataFrobotz"
        },
        {
          "status": "REGISTERED",
          "name": "erontest"
        }
      ]
    }

If you set ``--registration-status`` to ``DEPRECATED``, you will see deprecated domains (domains that can not register
new workflows or activities, but that can still be queried). For example::

    aws swf list-domains --registration-status DEPRECATED

Result::

    {
      "domainInfos": [
        {
          "status": "DEPRECATED",
          "name": "MyNeatNewDomain"
        }
      ]
    }


If you have many domains, you can set the ``--maximum-page-size`` option to limit the number of results returned. If
there are more results to return than the maximum number that you specified, you will receive a ``nextPageToken`` that
you can send to the next call to ``list-domains`` to retrieve additional entries.

Here's an example of using ``--maximum-page-size``::

    aws swf list-domains --registration-status REGISTERED --maximum-page-size 1

Result::

    {
      "domainInfos": [
        {
          "status": "REGISTERED",
          "name": "DataFrobotz"
        }
      ],
      "nextPageToken": "AAAAKgAAAAEAAAAAAAAAA2QJKNtidVgd49TTeNwYcpD+QKT2ynuEbibcQWe2QKrslMGe63gpS0MgZGpcpoKttL4OCXRFn98Xif557it+wSZUsvUDtImjDLvguyuyyFdIZtvIxIKEOPm3k2r4OjAGaFsGOuVbrKljvla7wdU7FYH3OlkNCP8b7PBj9SBkUyGoiAghET74P93AuVIIkdKGtQ=="
    }

When you make the call again, this time supplying the value of ``nextPageToken`` in the ``--next-page-token`` argument,
you'll get another page of results::

    aws swf list-domains --registration-status REGISTERED --maximum-page-size 1 --next-page-token "AAAAKgAAAAEAAAAAAAAAA2QJKNtidVgd49TTeNwYcpD+QKT2ynuEbibcQWe2QKrslMGe63gpS0MgZGpcpoKttL4OCXRFn98Xif557it+wSZUsvUDtImjDLvguyuyyFdIZtvIxIKEOPm3k2r4OjAGaFsGOuVbrKljvla7wdU7FYH3OlkNCP8b7PBj9SBkUyGoiAghET74P93AuVIIkdKGtQ=="

Result::

    {
      "domainInfos": [
        {
          "status": "REGISTERED",
          "name": "erontest"
        }
      ]
    }

When there are no further pages of results to retrieve, ``nextPageToken`` will not be returned in the results.

See Also
--------

-  `ListDomains <http://docs.aws.amazon.com/amazonswf/latest/apireference/API_ListDomains.html>`__
   in the *Amazon Simple Workflow Service API Reference*

