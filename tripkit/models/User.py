#!/usr/bin/env python
# Kyle Fitzsimmons, 2018


class User(object):
    '''
    :param db_user:     The ``peewee`` survey response for a given user.
    :ivar list trips:   A user's detected trips. This is only loaded
                        automatically on the ``User`` initialized
                        by :py:meth:`tripkit.database.Database.load_user`,
                        this must be called again if trips are detected and
                        saved to the cache.

    :vartype trips:     list
    '''

    def __init__(self, db_user):
        self.uuid = db_user.uuid
        self.coordinates = db_user.coordinates
        self.cancelled_prompt_responses = db_user.cancelled_prompts
        self.prompt_responses = db_user.prompts
        self.survey_response = {k: getattr(db_user, k) for k in db_user._meta.fields.keys()}
        self.detected_trip_coordinates = db_user.detected_trip_coordinates
        self.detected_trip_day_summaries = db_user.detected_trip_day_summaries
        self.user_locations = db_user.user_locations
        self.trips = []

    def __repr__(self):
        return f"<tripkit.models.User uuid={self.uuid}>"
