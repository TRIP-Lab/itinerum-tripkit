#!/usr/bin/env python
# Kyle Fitzsimmons, 2018


class User(object):
    """
    :param uuid: The uuid for the given user.

    :ivar iter coordinates:                User's coordinates as  a ``peewee`` foreign
                                           key attribute.
    :ivar iter cancelled_prompt_responses: User's cancelled prompts as a ``peewee`` foreign
                                           key attribute.
    :ivar iter prompt_responses:           User's prompt responses as a ``peewee`` foreign
                                           key relation.
    :ivar dict trips:                      A user's detected trips. This is only loaded 
                                           automatically on the ``User`` initialized
                                           by :py:meth:`datakit.database.Database.load_user`,
                                           this must be called again if trips are detected and
                                           saved to the cache.
    :vartype coordinates: iter
    :vartype cancelled_prompt_responses: iter
    :vartype prompt_responses: iter
    :vartype trips: dict
    """

    def __init__(self, uuid):
        self.uuid = uuid
        self.coordinates = []
        self.cancelled_prompt_responses = []
        self.prompt_responses = []
        self.trips = {}

    def __repr__(self):
        return '<User uuid={}>'.format(self.uuid)
