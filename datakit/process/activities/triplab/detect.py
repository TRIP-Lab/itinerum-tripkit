#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from geopy.distance import distance


labeled_coordinates = {
    'unlabeled': [],
    'commuting': [],
    'home': []
}
activity_label_proximity_m = 30.



def label_by_proximity(locations, c):
    for name, location in locations.items():
        delta_m = distance((c.latitude, c.longitude),
                           (location.latitude, location.longitude)).meters
        if delta_m <= activity_label_proximity_m:
            labeled_coordinates[name].append(c)


def run(coordinates, timezone, locations=None):
    if not locations:
        print('No activity locations to detect.')
        return
    for name in locations:
        labeled_coordinates.setdefault(name, [])

    start_time = coordinates[0].timestamp_UTC
    end_time = coordinates[-1].timestamp_UTC
    
    print(start_time, end_time)
    # last_c = None
    for c in coordinates:
        # if not last_c:
        #     last_c = c
        # delta_m = distance((c.latitude, c.longitude),
        #                    (last_c.latitude, last_c.longitude)).meters
        label_by_proximity(locations, c)
        # last_c = c
        assert abs(c.latitude) > 0.01 and abs(c.longitude) > 0.01

    total_labeled = 0
    for key, values in labeled_coordinates.items():
        total_labeled += len(values)
    print(total_labeled)
    print(len(coordinates))
