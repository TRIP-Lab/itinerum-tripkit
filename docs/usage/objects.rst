Library Objects
===============

..  _UserObjectAnchor:

User
----
The ``User`` object provides the representation of a user in a survey with their
associated coordinates, prompt, cancelled prompts and trips (if available in cache).

..  autoclass:: datakit.models.User
    :members:


Trip
----
The ``Trip`` object provides the representation of a user's trip with some inferred
properties about it.

..  autoclass:: datakit.models.Trip
	:members:


Trip Point
----------
The ``TripPoint`` object provides the respresentation of a user's GPS coordinates
after having been processed by a trip detection algorithm.

..  autoclass:: datakit.models.TripPoint
	:members:
