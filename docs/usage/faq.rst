FAQ
===


Q: Why are there additional points with duplicate timestamps in my detected trips?
A: Trip detection creates a labeled, uninterrupted trajectory from a user's coordinates. Occasionally gaps occur between trips, either
because of device handling of geofences, signal loss due to interference or battery drain, or a user temporarily pausing data collection. When this occurs,
a missing trip will be generated. If a missing trip is sufficiently small and immediately proceding a detected complete trip, it will be prepended to the complete
trip. When this occurs, a new point is generated with the end location of the previous trip and the same timestamp as the start (now the second point) of the next complete trip.