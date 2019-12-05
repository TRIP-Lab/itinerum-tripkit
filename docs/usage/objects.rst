Library Objects
===============

..  _UserObjectAnchor:

User
----
The :py:class:`tripkit.models.User` object provides the representation of a user in a survey with their
associated coordinates, prompt, cancelled prompts and trips (if available in cache).

..  autoclass:: tripkit.models.User
    :members:


Trip
----
The :py:class:`tripkit.models.Trip` object provides the representation of a user's trip with some inferred
properties about it.

..  autoclass:: tripkit.models.Trip
	:members:


Trip Point
----------
The :py:class:`tripkit.models.TripPoint` object provides the respresentation of a user's GPS coordinates
after having been processed by a trip detection algorithm.

..  autoclass:: tripkit.models.TripPoint
	:members:

Day Summary
-----------
The :py:class:`tripkit.models.DaySummary` object provides the representation of complete trip days after
processing a user's trips by a complete days detection algorithm.

..  autoclass:: tripkit.models.DaySummary
	:members:
