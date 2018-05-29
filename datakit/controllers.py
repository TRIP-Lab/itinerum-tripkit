#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from .database import (UserSurveyResponse, Coordinate, PromptResponse, CancelledPromptResponse, 
                       DetectedTripCoordinate, SubwayStationEntrance)

from .models.Trip import Trip
from .models.TripPoint import TripPoint
from .models.User import User



def load_user_from_db(uuid, start=None, end=None):
    db_user = UserSurveyResponse.get(uuid=uuid)
    
    user = User(uuid=uuid)
    user.coordinates = db_user.coordinates
    user.prompt_responses = db_user.prompts
    user.cancelled_prompt_responses = db_user.cancelled_prompts

    if start:
        user.coordinates = user.coordinates.where(Coordinate.timestamp_UTC >= start)
        user.prompt_responses = user.prompt_responses.where(PromptResponse.displayed_at_UTC >= start)
        user.cancelled_prompt_responses = (user.cancelled_prompt_responses
                                               .where(CancelledPromptResponse.displayed_at_UTC >= start))
    if end:
        user.coordinates = user.coordinates.where(Coordinate.timestamp_UTC <= end)
        user.prompt_responses = user.prompt_responses.where(PromptResponse.displayed_at_UTC <= end)
        user.cancelled_prompt_responses = (user.cancelled_prompt_responses
                                               .where(CancelledPromptResponse.displayed_at_UTC <= end))

    for c in db_user.detected_trip_coordinates:
        if start and c.timestamp_UTC <= start:
            continue
        if end and c.timestamp_UTC >= end:
            continue

        point = TripPoint(latitude=c.latitude,
                          longitude=c.longitude,
                          h_accuracy=c.h_accuracy,
                          timestamp_UTC=c.timestamp_UTC)

        if not c.trip_num in user.trips:
            user.trips[c.trip_num] = Trip(num=c.trip_num, trip_code=c.trip_code)
        user.trips[c.trip_num].points.append(point)

    return user


def save_trips(detected_trips):
    DetectedTripCoordinate.drop_table()
    DetectedTripCoordinate.create_table()
    for c in detected_trips:
        # TODO: this would be more consistent if trip coordinates
        # were named tuples for dot attributes
        DetectedTripCoordinate.create(user=c['uuid'],
                                      trip_num=c['trip'],
                                      trip_code=c['trip_code'],
                                      latitude=c['latitude'],
                                      longitude=c['longitude'],
                                      h_accuracy=c['h_accuracy'],
                                      timestamp_UTC=c['timestamp_UTC'])
