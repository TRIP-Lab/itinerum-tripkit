.. _OutputsPage:

=======
Outputs
=======


Complete Days
=============

The Complete Days/Trip Lab process iterates over the trips by 24-hour cycle (00:00:00-23:59:59) in the supplied timezone. For each day that a user participates in a study, the process checks if any trips are labeled as missing and if none exist, the day is labelled as "is_complete". If no trips exist, the day is not labeled as complete.

Special cases:

* It is common that a user may legitimately make no trips on a participation day. In the case that there is a day without any trips, but the day prior and after are labeled complete and the distance between the last trip end and the next trip start is <= 750 meters, this day will be labeled "is_complete". Cases with more than 1 day without trips are not considered by this rule.

Notes:

* The output results are grouped by ``uuid`` and ordered by ``date``.
* Boolean values are represented as ``1`` (True) or ``0`` (False).


.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

=============================== =========================================================
``uuid``                        The unique user ID in the survey.
``date``                        The date (localized by timezone) for complete day record.
``has_trips``                   Boolean to indicate whether date contains any trips.
``is_complete``					Boolean to indicate if date contains trips and no missing
								trips.
``start_latitude``				The latitude of the date's first trip.
``start_longitude``				The longitude of the date's first trip.
``end_latitude``				The latitude of the date's last trip.
``end_longitude``				The longitude of the date's last trip.
``consecutive_inactive_days``	The current tally of inactive days in a row (reset each
								complete day).
``inactivity_streak``			The maximum tally of incomplete days in a row for a user.
=============================== =========================================================
