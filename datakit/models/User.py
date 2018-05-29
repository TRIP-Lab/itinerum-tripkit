#!/usr/bin/env python
# Kyle Fitzsimmons, 2018


class User(object):
    def __init__(self, uuid):
        self.uuid = uuid
        self.coordinates = []
        self.cancelled_prompt_responses = []
        self.prompt_responses = []
        self.trips = {}

    def __repr__(self):
        return '<User uuid={}>'.format(self.uuid)
