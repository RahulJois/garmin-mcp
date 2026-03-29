"""
Schema context strings passed to Gemini for each health domain.

Notes for all schemas:
- DATE columns are stored as 'YYYY-MM-DD'
- DATETIME columns are stored as 'YYYY-MM-DD HH:MM:SS'
- TIME columns are stored as 'HH:MM:SS' strings (e.g. '01:30:00' = 90 minutes)
  To convert TIME to minutes: (CAST(SUBSTR(col,1,2) AS INTEGER)*60 + CAST(SUBSTR(col,4,2) AS INTEGER))
  To convert TIME to hours:   (CAST(SUBSTR(col,1,2) AS INTEGER) + CAST(SUBSTR(col,4,2) AS INTEGER)/60.0)
- Weight is in kilograms, distance in meters, speed in m/s
- Heart rate in bpm, stress 0-100, body battery 0-100
"""

SLEEP = """
Database: garmin.db

Table: sleep
  day          DATE PRIMARY KEY  -- one row per night, date of sleep END (morning)
  start        DATETIME          -- sleep start time
  end          DATETIME          -- sleep end time
  total_sleep  TIME              -- total sleep duration 'HH:MM:SS'
  deep_sleep   TIME              -- deep sleep duration
  light_sleep  TIME              -- light sleep duration
  rem_sleep    TIME              -- REM sleep duration
  awake        TIME              -- time spent awake during sleep window
  avg_spo2     FLOAT             -- average blood oxygen %
  avg_rr       FLOAT             -- average respiration rate (breaths/min)
  avg_stress   FLOAT             -- average stress during sleep
  score        INTEGER           -- Garmin sleep score (0-100)
  qualifier    VARCHAR           -- e.g. 'GOOD', 'FAIR', 'POOR'

Table: sleep_events
  timestamp  DATETIME PRIMARY KEY  -- when the event occurred
  event      VARCHAR               -- event type (e.g. 'deep_sleep', 'rem_sleep', 'wake')
  duration   TIME                  -- duration of this sleep phase
"""

HEART_RATE = """
Database: garmin.db

Table: resting_hr
  day                DATE PRIMARY KEY
  resting_heart_rate FLOAT  -- resting heart rate in bpm

Table: daily_summary (heart rate columns only)
  day     DATE PRIMARY KEY
  hr_min  INTEGER  -- minimum HR of the day (bpm)
  hr_max  INTEGER  -- maximum HR of the day (bpm)
  rhr     INTEGER  -- resting heart rate (bpm)

Database: garmin_monitoring.db  (reference as: monitoring.<table>)

Table: monitoring.monitoring_hr
  timestamp   DATETIME PRIMARY KEY  -- one reading every ~2 minutes throughout the day
  heart_rate  INTEGER               -- heart rate in bpm
"""

STRESS = """
Database: garmin.db

Table: stress
  timestamp  DATETIME PRIMARY KEY  -- one reading every ~3 minutes
  stress     INTEGER               -- stress level 0-100 (0-25 rest, 26-50 low, 51-75 medium, 76-100 high)

Table: daily_summary (stress columns only)
  day         DATE PRIMARY KEY
  stress_avg  INTEGER  -- average stress for the day (0-100)
"""

BODY_BATTERY = """
Database: garmin.db

Table: daily_summary (body battery columns only)
  day         DATE PRIMARY KEY
  bb_charged  INTEGER  -- body battery charged during the day
  bb_max      INTEGER  -- maximum body battery level (0-100)
  bb_min      INTEGER  -- minimum body battery level (0-100, lowest during the day)
"""

WEIGHT = """
Database: garmin.db

Table: weight
  day     DATE PRIMARY KEY
  weight  FLOAT  -- body weight in kilograms
"""

SPO2_RESPIRATION = """
Database: garmin.db

Table: sleep (SpO2 and respiration during sleep)
  day      DATE PRIMARY KEY
  avg_spo2 FLOAT  -- average blood oxygen % during sleep
  avg_rr   FLOAT  -- average respiration rate (breaths/min) during sleep

Table: daily_summary (SpO2 columns)
  day          DATE PRIMARY KEY
  spo2_avg     FLOAT  -- average SpO2 during the day %
  spo2_min     FLOAT  -- minimum SpO2 during the day %
  rr_waking_avg FLOAT -- average waking respiration rate (breaths/min)
  rr_max       FLOAT  -- max respiration rate
  rr_min       FLOAT  -- min respiration rate

Database: garmin_monitoring.db  (reference as: monitoring.<table>)

Table: monitoring.monitoring_pulse_ox
  timestamp  DATETIME PRIMARY KEY
  pulse_ox   FLOAT  -- blood oxygen % reading

Table: monitoring.monitoring_rr
  timestamp  DATETIME PRIMARY KEY
  rr         FLOAT  -- respiration rate (breaths/min)
"""

ACTIVITIES = """
Database: garmin_activities.db

Table: activities
  activity_id              VARCHAR PRIMARY KEY
  name                     VARCHAR   -- activity name/title
  description              VARCHAR
  type                     VARCHAR   -- activity type string
  sport                    VARCHAR   -- e.g. 'running', 'cycling', 'swimming', 'walking'
  sub_sport                VARCHAR   -- e.g. 'trail', 'road', 'open_water'
  training_effect          FLOAT     -- aerobic training effect (1.0-5.0)
  anaerobic_training_effect FLOAT    -- anaerobic training effect (1.0-5.0)
  start_time               DATETIME
  stop_time                DATETIME
  elapsed_time             TIME      -- total elapsed time 'HH:MM:SS'
  moving_time              TIME      -- actual moving time 'HH:MM:SS'
  distance                 FLOAT     -- distance in meters
  calories                 INTEGER
  avg_hr                   INTEGER   -- average heart rate (bpm)
  max_hr                   INTEGER
  avg_rr                   FLOAT     -- average respiration rate
  avg_cadence              INTEGER
  max_cadence              INTEGER
  avg_speed                FLOAT     -- average speed m/s
  max_speed                FLOAT
  ascent                   FLOAT     -- total ascent in meters
  descent                  FLOAT
  avg_temperature          FLOAT     -- Celsius
  max_temperature          FLOAT
  min_temperature          FLOAT
  start_lat                FLOAT     -- GPS coordinates
  start_long               FLOAT
  hrz_1_time               TIME      -- time in HR zone 1 (warm-up)
  hrz_2_time               TIME      -- time in HR zone 2 (easy)
  hrz_3_time               TIME      -- time in HR zone 3 (aerobic)
  hrz_4_time               TIME      -- time in HR zone 4 (threshold)
  hrz_5_time               TIME      -- time in HR zone 5 (max)

Table: steps_activities  (JOIN on activity_id for runs/walks)
  activity_id          VARCHAR PRIMARY KEY
  steps                INTEGER
  avg_pace             TIME     -- average pace 'MM:SS' per km
  avg_moving_pace      TIME
  max_pace             TIME
  avg_steps_per_min    INTEGER  -- cadence (spm)
  avg_step_length      FLOAT    -- meters
  vo2_max              FLOAT    -- estimated VO2 max (ml/kg/min)

Table: cycle_activities  (JOIN on activity_id for bike rides)
  activity_id  VARCHAR PRIMARY KEY
  strokes      INTEGER
  vo2_max      FLOAT

Table: paddle_activities  (JOIN on activity_id for paddle sports)
  activity_id       VARCHAR PRIMARY KEY
  strokes           INTEGER
  avg_stroke_distance FLOAT
"""

ACTIVITY_DETAIL = """
Database: garmin_activities.db

Table: activity_laps
  activity_id   VARCHAR  -- foreign key to activities.activity_id
  lap           INTEGER  -- lap number (1-based)
  start_time    DATETIME
  stop_time     DATETIME
  elapsed_time  TIME
  moving_time   TIME
  distance      FLOAT    -- meters
  calories      INTEGER
  avg_hr        INTEGER  -- bpm
  max_hr        INTEGER
  avg_speed     FLOAT    -- m/s
  max_speed     FLOAT
  avg_cadence   INTEGER
  ascent        FLOAT
  descent       FLOAT
  avg_temperature FLOAT
  PRIMARY KEY (activity_id, lap)

Table: activity_records
  activity_id    VARCHAR   -- foreign key to activities.activity_id
  record         INTEGER   -- record number within activity
  timestamp      DATETIME
  position_lat   FLOAT
  position_long  FLOAT
  distance       FLOAT     -- cumulative distance in meters
  cadence        INTEGER
  altitude       FLOAT     -- meters
  hr             INTEGER   -- heart rate bpm
  rr             FLOAT     -- respiration rate
  speed          FLOAT     -- m/s
  temperature    FLOAT     -- Celsius
  PRIMARY KEY (activity_id, record)

Table: activities  (for filtering by date/sport when getting detail)
  activity_id  VARCHAR PRIMARY KEY
  sport        VARCHAR
  start_time   DATETIME
  name         VARCHAR
"""

DAILY_SUMMARY = """
Database: garmin.db

Table: daily_summary
  day                  DATE PRIMARY KEY
  steps                INTEGER   -- total steps
  step_goal            INTEGER   -- daily step goal
  distance             FLOAT     -- total distance in meters
  floors_up            FLOAT     -- floors climbed
  floors_down          FLOAT
  floors_goal          FLOAT
  calories_total       INTEGER   -- total calories burned
  calories_bmr         INTEGER   -- basal metabolic rate calories
  calories_active      INTEGER   -- active calories
  calories_goal        INTEGER
  calories_consumed    INTEGER   -- food calories logged
  hydration_goal       INTEGER   -- ml
  hydration_intake     INTEGER   -- ml consumed
  sweat_loss           INTEGER   -- ml
  moderate_activity_time  TIME   -- time in moderate intensity
  vigorous_activity_time  TIME   -- time in vigorous intensity
  intensity_time_goal     TIME   -- weekly intensity minute goal (daily allocation)
  hr_min               INTEGER   -- min heart rate of day
  hr_max               INTEGER   -- max heart rate of day
  rhr                  INTEGER   -- resting heart rate
  stress_avg           INTEGER   -- average stress (0-100)
  bb_max               INTEGER   -- body battery max
  bb_min               INTEGER   -- body battery min
  description          VARCHAR
"""

TRENDS = """
Database: garmin_summary.db

Table: days_summary   (one row per day — aggregated daily stats)
  day               DATE PRIMARY KEY
  hr_avg            FLOAT   -- average heart rate
  hr_min            FLOAT
  hr_max            FLOAT
  rhr_avg           FLOAT   -- resting heart rate
  weight_avg        FLOAT   -- kg
  steps             INTEGER
  steps_goal        INTEGER
  floors            FLOAT
  sleep_avg         TIME    -- average sleep duration
  rem_sleep_avg     TIME
  stress_avg        INTEGER
  calories_avg      INTEGER
  calories_goal     INTEGER
  activities        INTEGER -- number of activities
  activities_calories INTEGER
  activities_distance INTEGER -- meters
  spo2_avg          FLOAT
  rr_waking_avg     FLOAT

Table: weeks_summary  (one row per week, first_day = Monday)
  first_day         DATE PRIMARY KEY
  hr_avg            FLOAT
  rhr_avg           FLOAT
  weight_avg        FLOAT
  steps             INTEGER
  sleep_avg         TIME
  rem_sleep_avg     TIME
  stress_avg        INTEGER
  calories_avg      INTEGER
  activities        INTEGER
  activities_distance INTEGER
  intensity_time    TIME    -- total weekly intensity time
  spo2_avg          FLOAT
  bb_max            INTEGER
  bb_min            INTEGER

Table: months_summary (one row per month, first_day = 1st of month)
  first_day         DATE PRIMARY KEY
  hr_avg            FLOAT
  rhr_avg           FLOAT
  weight_avg        FLOAT   -- kg
  weight_min        FLOAT
  weight_max        FLOAT
  steps             INTEGER
  sleep_avg         TIME
  rem_sleep_avg     TIME
  stress_avg        INTEGER
  calories_avg      INTEGER
  activities        INTEGER
  activities_distance INTEGER
  intensity_time    TIME
  spo2_avg          FLOAT
  bb_max            INTEGER
  bb_min            INTEGER

Table: years_summary  (one row per year, first_day = Jan 1)
  first_day         DATE PRIMARY KEY
  hr_avg            FLOAT
  rhr_avg           FLOAT
  weight_avg        FLOAT
  steps             INTEGER
  sleep_avg         TIME
  stress_avg        INTEGER
  calories_avg      INTEGER
  activities        INTEGER
  activities_distance INTEGER
  intensity_time    TIME
  spo2_avg          FLOAT
"""

# Domain registry: maps domain name → description, schema, and DB config.
# Used by the list_domains and get_schema MCP tools.
DOMAINS = {
    "sleep": {
        "description": "Sleep duration, stages (deep/light/REM), sleep score and quality, bedtime/wake time, SpO2 and respiration rate during sleep.",
        "schema": SLEEP,
        "primary_db": "garmin",
        "attach_dbs": {},
    },
    "heart_rate": {
        "description": "Resting heart rate, daily min/max HR, and intraday heart rate readings (~2-min resolution). Uses garmin.db + garmin_monitoring.db (attach as 'monitoring').",
        "schema": HEART_RATE,
        "primary_db": "garmin",
        "attach_dbs": {"monitoring": "garmin_monitoring"},
    },
    "stress": {
        "description": "Stress level readings (~3-min resolution, 0-100 scale) and daily average stress. 0-25 resting, 26-50 low, 51-75 medium, 76-100 high.",
        "schema": STRESS,
        "primary_db": "garmin",
        "attach_dbs": {},
    },
    "body_battery": {
        "description": "Garmin Body Battery energy levels: daily max, min, and charged amount (all 0-100 scale).",
        "schema": BODY_BATTERY,
        "primary_db": "garmin",
        "attach_dbs": {},
    },
    "weight": {
        "description": "Body weight measurements over time, stored in kilograms.",
        "schema": WEIGHT,
        "primary_db": "garmin",
        "attach_dbs": {},
    },
    "spo2_respiration": {
        "description": "Blood oxygen saturation (SpO2 %) and respiration rate (breaths/min). Covers sleep averages, daily summaries, and intraday readings. Uses garmin.db + garmin_monitoring.db (attach as 'monitoring').",
        "schema": SPO2_RESPIRATION,
        "primary_db": "garmin",
        "attach_dbs": {"monitoring": "garmin_monitoring"},
    },
    "activities": {
        "description": "Workout activity summaries: runs, rides, walks, swims, paddle sports. Includes distance, pace, duration, HR zones, calories, VO2 max, training effect, ascent/descent.",
        "schema": ACTIVITIES,
        "primary_db": "garmin_activities",
        "attach_dbs": {},
    },
    "activity_detail": {
        "description": "Per-lap and per-second detail within a specific activity: splits, heart rate curves, GPS coordinates, elevation, cadence, speed.",
        "schema": ACTIVITY_DETAIL,
        "primary_db": "garmin_activities",
        "attach_dbs": {},
    },
    "daily_summary": {
        "description": "Daily health rollups: steps, distance, floors, calories (total/active/BMR/consumed), hydration, sweat loss, moderate and vigorous activity minutes.",
        "schema": DAILY_SUMMARY,
        "primary_db": "garmin",
        "attach_dbs": {},
    },
    "trends": {
        "description": "Aggregated health trends by day, week, month, and year. Covers HR, RHR, weight, steps, sleep, stress, calories, activities, SpO2, body battery, intensity time. Best for long-term trend analysis.",
        "schema": TRENDS,
        "primary_db": "garmin_summary",
        "attach_dbs": {},
    },
}
