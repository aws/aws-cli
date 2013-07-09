Customizations
==============

As we start to accumulate more and more of these *built-in* customizations
we probably need to come up with some way to organize them and to make
it easy to add them and register them.

One idea I had was to place them all with a package like this.  That
at least keeps them all in one place.  Each module in this package
should contain a single customization (I think).

To take it a step further, we could have each module define a couple
of well-defined attributes:

* ``EVENT`` would be a string containing the event that this customization
  needs to be registered with.  Or, perhaps this should be a list of
  events?
* ``handler`` is a callable that will be registered as the handler
  for the event.

Using a convention like this, we could perhaps automatically discover
all customizations and register them without having to manually edit
``handlers.py`` each time.
