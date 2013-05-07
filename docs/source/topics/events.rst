Botocore Events
===============

Botocore will emit events during various parts of its execution.  Users of the
library can register handlers (callables) for these events, such that whenever
an event is emitted, all registered handlers for the event will be called.
This allows you to customize and extend the behavior of botocore without having
to modify the internals.  This document covers this event system in detail.

Session Events
--------------

The main interface for events is through the :class:`botocore.session.Session`
class.  The ``Session`` object allows you to register and unregister handlers
to events.


Event Types
-----------

The table below shows all of the events emitted by botocore.  In some cases,
the events are listed as ``<service>.<operations>.bar``, in which ``<service>``
and ``<operation>`` are replaced with a specific service and operation, for
example ``s3.ListObjects.bar``.

.. list-table:: Events
   :header-rows: 1

   * - Event Name
     - Occurance
     - Arguments
     - Return Value
   * - **service-created**
     - Whenever a service is created via the Sessions ``get_service``
       method.
     - ``service`` - The newly created :class:`botocore.service.Service`
       object.
     - Ignored.
   * - **before-call.<service>.<operation>**
     - When an operation is being called (``Operation.call``).
     - ``operation`` - The newly created :class:`botocore.operation.Operation`
       object.
     - Ignored.
   * - **after-call.<service>.<operation>**
     - After an operation has been called, but before the response is parsed.
     - ``response`` - The HTTP response, ``parsed`` - The parsed data.
     - Ignored.


Event Emission
--------------

When an event is emitted, the handlers are invoked in the order that they were
registered.
