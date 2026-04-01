"""
Schema context strings passed to Gemini for each health domain.

Notes for all schemas:
- DATE columns are stored as 'YYYY-MM-DD'
- DATETIME columns are stored as 'YYYY-MM-DD HH:MM:SS'
- TIME columns are stored as 'HH:MM:SS' strings (e.g. '01:30:00' = 90 minutes)
  To convert TIME to minutes: (CAST(SUBSTR(col,1,2) AS INTEGER)*60 + CAST(SUBSTR(col,4,2) AS INTEGER))
  To convert TIME to hours:   (CAST(SUBSTR(col,1,2) AS INTEGER) + CAST(SUBSTR(col,4,2) AS INTEGER)/60.0)
- Weight is in kilograms, distance in kilometers, speed in m/s
- Heart rate in bpm, stress 0-100, body battery 0-100
"""

SLEEP = """
Database: garmin.db

Table: sleep
  day          DATE PRIMARY KEY  -- one row per night, date of sleep END (morning)
  start        DATETIME          -- sleep start time
  end          DATETIME          -- sleep end time
  total_sleep  TIME              -- total sleep duration 'HH:MM:SS.ffffff'
  deep_sleep   TIME              -- deep sleep duration 'HH:MM:SS.ffffff'
  light_sleep  TIME              -- light sleep duration 'HH:MM:SS.ffffff'
  rem_sleep    TIME              -- REM sleep duration 'HH:MM:SS.ffffff'
  awake        TIME              -- time spent awake during sleep window 'HH:MM:SS.ffffff'
  avg_spo2     FLOAT             -- average blood oxygen % during sleep
  avg_rr       FLOAT             -- average respiration rate (breaths/min) during sleep
  avg_stress   FLOAT             -- average stress during sleep (0-100)
  score        INTEGER           -- Garmin sleep score (0-100)
  qualifier    VARCHAR           -- sleep quality rating ('EXCELLENT', 'GOOD', 'FAIR', 'POOR', 'INVALID')

Table: sleep_events
  timestamp  DATETIME PRIMARY KEY  -- when the event occurred
  event      VARCHAR               -- event type ('deep_sleep', 'light_sleep', 'rem_sleep', 'awake')
  duration   TIME                  -- duration of this sleep phase 'HH:MM:SS.ffffff'
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
  timestamp   DATETIME PRIMARY KEY  -- one reading approximately every minute throughout the day
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
  course_id                VARCHAR   -- associated course ID if any
  laps                     INTEGER   -- number of laps in activity
  sport                    VARCHAR   -- e.g. 'running', 'cycling', 'swimming', 'walking'
  sub_sport                VARCHAR   -- e.g. 'trail', 'road', 'open_water'
  training_effect          FLOAT     -- aerobic training effect (1.0-5.0)
  anaerobic_training_effect FLOAT    -- anaerobic training effect (1.0-5.0)
  start_time               DATETIME
  stop_time                DATETIME
  elapsed_time             TIME      -- total elapsed time 'HH:MM:SS.ffffff'
  moving_time              TIME      -- actual moving time 'HH:MM:SS.ffffff'
  distance                 FLOAT     -- total distance in kilometers (km)
  cycles                   INTEGER
  calories                 INTEGER
  avg_hr                   INTEGER   -- average heart rate (bpm)
  max_hr                   INTEGER   -- maximum heart rate (bpm)
  avg_rr                   FLOAT     -- average respiration rate
  max_rr                   FLOAT     -- maximum respiration rate
  avg_cadence              INTEGER   -- average cadence
  max_cadence              INTEGER   -- maximum cadence
  avg_speed                FLOAT     -- average speed km/h
  max_speed                FLOAT     -- maximum speed km/h
  ascent                   FLOAT     -- total ascent in meters
  descent                  FLOAT     -- total descent in meters
  avg_temperature          FLOAT     -- average temperature Celsius
  max_temperature          FLOAT     -- maximum temperature Celsius
  min_temperature          FLOAT     -- minimum temperature Celsius
  start_lat                FLOAT     -- activity start latitude
  start_long               FLOAT     -- activity start longitude
  stop_lat                 FLOAT     -- activity end latitude
  stop_long                FLOAT     -- activity end longitude
  hr_zones_method          VARCHAR   -- e.g. 'max_heart_rate'
  hrz_1_hr                 INTEGER   -- heart rate zone 1 threshold (bpm)
  hrz_2_hr                 INTEGER   -- heart rate zone 2 threshold (bpm)
  hrz_3_hr                 INTEGER   -- heart rate zone 3 threshold (bpm)
  hrz_4_hr                 INTEGER   -- heart rate zone 4 threshold (bpm)
  hrz_5_hr                 INTEGER   -- heart rate zone 5 threshold (bpm)
  hrz_1_time               TIME      -- time in HR zone 1 (warm-up) 'HH:MM:SS.ffffff'
  hrz_2_time               TIME      -- time in HR zone 2 (easy) 'HH:MM:SS.ffffff'
  hrz_3_time               TIME      -- time in HR zone 3 (aerobic) 'HH:MM:SS.ffffff'
  hrz_4_time               TIME      -- time in HR zone 4 (threshold) 'HH:MM:SS.ffffff'
  hrz_5_time               TIME      -- time in HR zone 5 (max) 'HH:MM:SS.ffffff'

Table: steps_activities  (JOIN on activity_id for runs/walks)
  activity_id             VARCHAR PRIMARY KEY
  steps                   INTEGER
  avg_pace                TIME     -- average pace 'MM:SS.ffffff' per km
  avg_moving_pace         TIME     -- average pace during moving time 'MM:SS.ffffff'
  max_pace                TIME     -- maximum pace 'MM:SS.ffffff' per km
  avg_steps_per_min       INTEGER  -- cadence (steps/min)
  max_steps_per_min       INTEGER  -- maximum steps per minute
  avg_step_length         FLOAT    -- average step length in meters
  avg_vertical_ratio      FLOAT    -- average vertical ratio %
  avg_vertical_oscillation FLOAT   -- average vertical oscillation in cm
  avg_gct_balance         FLOAT    -- average ground contact time balance %
  avg_ground_contact_time TIME     -- average ground contact time 'HH:MM:SS.ffffff'
  avg_stance_time_percent FLOAT    -- average stance time %
  vo2_max                 FLOAT    -- estimated VO2 max (ml/kg/min)

# Table: cycle_activities  (JOIN on activity_id for bike rides)
#   activity_id  VARCHAR PRIMARY KEY
#   strokes      INTEGER
#   vo2_max      FLOAT

# Table: paddle_activities  (JOIN on activity_id for paddle sports)
#   activity_id       VARCHAR PRIMARY KEY
#   strokes           INTEGER
#   avg_stroke_distance FLOAT
"""

ACTIVITY_MONITORING = """
Database: garmin_monitoring.db

Table: monitoring.monitoring
  timestamp           DATETIME PRIMARY KEY  -- activity log timestamp (irregular intervals, not uniform)
  activity_type       VARCHAR               -- detected activity type (e.g. 'running', 'walking', 'cycling', 'generic', 'stop_disable')
  intensity           INTEGER               -- activity intensity level (e.g. 0-4 for running)
  duration            TIME                  -- segment duration 'HH:MM:SS.ffffff' (cumulative for that segment)
  distance            FLOAT                 -- cumulative distance in meters (m) up to this timestamp
  cum_active_time     TIME                  -- cumulative active time 'HH:MM:SS.ffffff' up to this timestamp
  active_calories     INTEGER               -- cumulative active calories up to this timestamp
  steps               INTEGER               -- cumulative steps up to this timestamp
  strokes             FLOAT                 -- cumulative swimming/paddle strokes up to this timestamp
  cycles              FLOAT                 -- cumulative cycling cycles up to this timestamp

Table: monitoring.monitoring_climb
  timestamp           DATETIME PRIMARY KEY  -- climb/elevation log timestamp (irregular intervals, not uniform)
  ascent              FLOAT                 -- ascent in meters (m) at this timestamp
  descent             FLOAT                 -- descent in meters (m) at this timestamp
  cum_ascent          FLOAT                 -- cumulative ascent in meters (m) up to this timestamp
  cum_descent         FLOAT                 -- cumulative descent in meters (m) up to this timestamp
"""

ACTIVITY_DETAIL = """
Database: garmin_activities.db

Table: activity_laps
  activity_id     VARCHAR  -- foreign key to activities.activity_id
  lap             INTEGER  -- lap number (starts from 0)
  start_time      DATETIME
  stop_time       DATETIME
  elapsed_time    TIME     -- lap elapsed time 'HH:MM:SS.ffffff'
  moving_time     TIME     -- lap moving time 'HH:MM:SS.ffffff'
  distance        FLOAT     -- lap distance in kilometers (km)
  cycles          INTEGER
  avg_hr          INTEGER  -- average heart rate (bpm)
  max_hr          INTEGER  -- maximum heart rate (bpm)
  avg_rr          FLOAT    -- average respiration rate
  max_rr          FLOAT    -- maximum respiration rate
  calories        INTEGER  -- lap calories
  avg_cadence     INTEGER  -- average cadence
  max_cadence     INTEGER  -- maximum cadence
  avg_speed       FLOAT    -- average speed m/s
  max_speed       FLOAT    -- maximum speed m/s
  ascent          FLOAT    -- lap ascent in meters
  descent         FLOAT    -- lap descent in meters
  avg_temperature FLOAT    -- average temperature Celsius
  max_temperature FLOAT    -- maximum temperature Celsius
  min_temperature FLOAT    -- minimum temperature Celsius
  start_lat       FLOAT    -- lap start latitude
  start_long      FLOAT    -- lap start longitude
  stop_lat        FLOAT    -- lap stop/end latitude
  stop_long       FLOAT    -- lap stop/end longitude
  hr_zones_method VARCHAR  -- e.g. 'max_heart_rate'
  hrz_1_hr        INTEGER  -- heart rate zone 1 threshold (bpm)
  hrz_2_hr        INTEGER  -- heart rate zone 2 threshold (bpm)
  hrz_3_hr        INTEGER  -- heart rate zone 3 threshold (bpm)
  hrz_4_hr        INTEGER  -- heart rate zone 4 threshold (bpm)
  hrz_5_hr        INTEGER  -- heart rate zone 5 threshold (bpm)
  hrz_1_time      TIME     -- time in HR zone 1 'HH:MM:SS.ffffff'
  hrz_2_time      TIME     -- time in HR zone 2 'HH:MM:SS.ffffff'
  hrz_3_time      TIME     -- time in HR zone 3 'HH:MM:SS.ffffff'
  hrz_4_time      TIME     -- time in HR zone 4 'HH:MM:SS.ffffff'
  hrz_5_time      TIME     -- time in HR zone 5 'HH:MM:SS.ffffff'
  PRIMARY KEY (activity_id, lap)

Table: activity_records
  activity_id    VARCHAR   -- foreign key to activities.activity_id
  record         INTEGER   -- record number within activity (sequential per-second data)
  timestamp      DATETIME  -- record timestamp
  position_lat   FLOAT     -- GPS latitude coordinate
  position_long  FLOAT     -- GPS longitude coordinate
  distance       FLOAT     -- cumulative distance in kilometers (km) at this record
  cadence        INTEGER   -- cadence (steps/min for running, rpm for cycling)
  altitude       FLOAT     -- altitude/elevation in meters
  hr             INTEGER   -- heart rate in bpm
  rr             FLOAT     -- respiration rate (breaths/min)
  speed          FLOAT     -- instantaneous speed in km/h
  temperature    FLOAT     -- temperature in Celsius
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
  day                     DATE PRIMARY KEY
  steps                   INTEGER   -- total steps
  step_goal               INTEGER   -- daily step goal
  distance                FLOAT     -- total distance in kilometers
  floors_up               FLOAT     -- floors climbed
  floors_down             FLOAT     -- floors descended
  floors_goal             FLOAT     -- daily floor goal
  calories_total          INTEGER   -- total calories burned
  calories_bmr            INTEGER   -- basal metabolic rate calories
  calories_active         INTEGER   -- active calories
  calories_goal           INTEGER   -- daily calorie goal
  calories_consumed       INTEGER   -- food calories logged
  hydration_goal          INTEGER   -- daily hydration goal in ml
  hydration_intake        INTEGER   -- ml consumed
  sweat_loss              INTEGER   -- ml
  moderate_activity_time  TIME      -- time in moderate intensity 'HH:MM:SS.ffffff'
  vigorous_activity_time  TIME      -- time in vigorous intensity 'HH:MM:SS.ffffff'
  intensity_time_goal     TIME      -- weekly intensity minute goal (daily allocation) 'HH:MM:SS.ffffff'
  hr_min                  INTEGER   -- minimum heart rate of day (bpm)
  hr_max                  INTEGER   -- maximum heart rate of day (bpm)
  rhr                     INTEGER   -- resting heart rate (bpm)
  stress_avg              INTEGER   -- average stress (0-100)
  spo2_avg                FLOAT     -- average blood oxygen % during day
  spo2_min                FLOAT     -- minimum blood oxygen % during day
  rr_waking_avg           FLOAT     -- average waking respiration rate (breaths/min)
  rr_max                  FLOAT     -- maximum respiration rate
  rr_min                  FLOAT     -- minimum respiration rate
  bb_charged              INTEGER   -- body battery charged during the day (0-100)
  bb_max                  INTEGER   -- body battery maximum (0-100)
  bb_min                  INTEGER   -- body battery minimum (0-100, lowest during day)
  description             VARCHAR
"""

TRENDS = """
Database: garmin_summary.db

Table: days_summary   (one row per day — aggregated daily stats)
  day                    DATE PRIMARY KEY
  hr_avg                 FLOAT     -- average heart rate
  hr_min                 INTEGER   -- minimum heart rate
  hr_max                 INTEGER   -- maximum heart rate
  rhr_avg                FLOAT     -- average resting heart rate
  rhr_min                INTEGER   -- minimum resting heart rate
  rhr_max                INTEGER   -- maximum resting heart rate
  inactive_hr_avg        FLOAT     -- average inactive/sedentary heart rate
  inactive_hr_min        INTEGER   -- minimum inactive heart rate
  inactive_hr_max        INTEGER   -- maximum inactive heart rate
  weight_avg             FLOAT     -- average weight (kg)
  weight_min             FLOAT     -- minimum weight (kg)
  weight_max             FLOAT     -- maximum weight (kg)
  intensity_time         TIME      -- total daily intensity time 'HH:MM:SS.ffffff'
  moderate_activity_time TIME      -- time in moderate intensity 'HH:MM:SS.ffffff'
  vigorous_activity_time TIME      -- time in vigorous intensity 'HH:MM:SS.ffffff'
  intensity_time_goal    TIME      -- daily intensity minute goal 'HH:MM:SS.ffffff'
  steps                  INTEGER   -- total daily steps
  steps_goal             INTEGER   -- daily step goal
  floors                 FLOAT     -- total floors climbed
  floors_goal            FLOAT     -- daily floor goal
  sleep_avg              TIME      -- average sleep duration 'HH:MM:SS.ffffff'
  sleep_min              TIME      -- minimum sleep duration 'HH:MM:SS.ffffff'
  sleep_max              TIME      -- maximum sleep duration 'HH:MM:SS.ffffff'
  rem_sleep_avg          TIME      -- average REM sleep 'HH:MM:SS.ffffff'
  rem_sleep_min          TIME      -- minimum REM sleep 'HH:MM:SS.ffffff'
  rem_sleep_max          TIME      -- maximum REM sleep 'HH:MM:SS.ffffff'
  stress_avg             FLOAT     -- average stress (0-100)
  calories_avg           FLOAT     -- average daily calories burned
  calories_bmr_avg       FLOAT     -- basal metabolic rate calories
  calories_active_avg    FLOAT     -- active calories
  calories_goal          INTEGER   -- daily calorie goal
  calories_consumed_avg  FLOAT     -- food calories logged
  activities             INTEGER   -- number of activities
  activities_calories    INTEGER   -- total calories from activities
  activities_distance    FLOAT     -- total distance from activities (km)
  hydration_goal         INTEGER   -- daily hydration goal (ml)
  hydration_avg          FLOAT     -- average hydration intake (ml)
  hydration_intake       INTEGER   -- total hydration intake (ml)
  sweat_loss_avg         FLOAT     -- average sweat loss (ml)
  sweat_loss             INTEGER   -- total sweat loss (ml)
  spo2_avg               FLOAT     -- average blood oxygen %
  spo2_min               FLOAT     -- minimum blood oxygen %
  rr_waking_avg          FLOAT     -- average waking respiration rate (breaths/min)
  rr_max                 FLOAT     -- maximum respiration rate
  rr_min                 FLOAT     -- minimum respiration rate
  bb_max                 FLOAT     -- body battery maximum (0-100)
  bb_min                 FLOAT     -- body battery minimum (0-100)

Table: weeks_summary  (one row per week, first_day = Thursday)
  first_day              DATE PRIMARY KEY
  hr_avg                 FLOAT     -- average heart rate
  hr_min                 INTEGER   -- minimum heart rate
  hr_max                 INTEGER   -- maximum heart rate
  rhr_avg                FLOAT     -- average resting heart rate
  rhr_min                INTEGER   -- minimum resting heart rate
  rhr_max                INTEGER   -- maximum resting heart rate
  inactive_hr_avg        FLOAT     -- average inactive/sedentary heart rate
  inactive_hr_min        INTEGER   -- minimum inactive heart rate
  inactive_hr_max        INTEGER   -- maximum inactive heart rate
  weight_avg             FLOAT     -- average weight (kg)
  weight_min             FLOAT     -- minimum weight (kg)
  weight_max             FLOAT     -- maximum weight (kg)
  intensity_time         TIME      -- total weekly intensity time 'HH:MM:SS.ffffff'
  moderate_activity_time TIME      -- time in moderate intensity 'HH:MM:SS.ffffff'
  vigorous_activity_time TIME      -- time in vigorous intensity 'HH:MM:SS.ffffff'
  intensity_time_goal    TIME      -- weekly intensity minute goal 'HH:MM:SS.ffffff'
  steps                  INTEGER   -- total weekly steps
  steps_goal             INTEGER   -- weekly step goal
  floors                 FLOAT     -- total floors climbed
  floors_goal            FLOAT     -- weekly floor goal
  sleep_avg              TIME      -- average sleep duration 'HH:MM:SS.ffffff'
  sleep_min              TIME      -- minimum sleep duration 'HH:MM:SS.ffffff'
  sleep_max              TIME      -- maximum sleep duration 'HH:MM:SS.ffffff'
  rem_sleep_avg          TIME      -- average REM sleep 'HH:MM:SS.ffffff'
  rem_sleep_min          TIME      -- minimum REM sleep 'HH:MM:SS.ffffff'
  rem_sleep_max          TIME      -- maximum REM sleep 'HH:MM:SS.ffffff'
  stress_avg             FLOAT     -- average stress (0-100)
  calories_avg           FLOAT     -- average daily calories burned
  calories_bmr_avg       FLOAT     -- average basal metabolic rate calories
  calories_active_avg    FLOAT     -- average active calories
  calories_goal          INTEGER   -- weekly calorie goal
  calories_consumed_avg  FLOAT     -- average food calories logged
  activities             INTEGER   -- total number of activities
  activities_calories    INTEGER   -- total calories from activities
  activities_distance    FLOAT     -- total distance from activities (km)
  hydration_goal         INTEGER   -- weekly hydration goal (ml)
  hydration_avg          FLOAT     -- average daily hydration intake (ml)
  hydration_intake       INTEGER   -- total weekly hydration intake (ml)
  sweat_loss_avg         FLOAT     -- average daily sweat loss (ml)
  sweat_loss             INTEGER   -- total weekly sweat loss (ml)
  spo2_avg               FLOAT     -- average blood oxygen %
  spo2_min               FLOAT     -- minimum blood oxygen %
  rr_waking_avg          FLOAT     -- average waking respiration rate (breaths/min)
  rr_max                 FLOAT     -- maximum respiration rate
  rr_min                 FLOAT     -- minimum respiration rate
  bb_max                 FLOAT     -- body battery maximum (0-100)
  bb_min                 FLOAT     -- body battery minimum (0-100)

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
  first_day              DATE PRIMARY KEY
  hr_avg                 FLOAT     -- average heart rate
  hr_min                 INTEGER   -- minimum heart rate
  hr_max                 INTEGER   -- maximum heart rate
  rhr_avg                FLOAT     -- average resting heart rate
  rhr_min                INTEGER   -- minimum resting heart rate
  rhr_max                INTEGER   -- maximum resting heart rate
  inactive_hr_avg        FLOAT     -- average inactive/sedentary heart rate
  inactive_hr_min        INTEGER   -- minimum inactive heart rate
  inactive_hr_max        INTEGER   -- maximum inactive heart rate
  weight_avg             FLOAT     -- average weight (kg)
  weight_min             FLOAT     -- minimum weight (kg)
  weight_max             FLOAT     -- maximum weight (kg)
  intensity_time         TIME      -- total yearly intensity time 'HH:MM:SS.ffffff'
  moderate_activity_time TIME      -- time in moderate intensity 'HH:MM:SS.ffffff'
  vigorous_activity_time TIME      -- time in vigorous intensity 'HH:MM:SS.ffffff'
  intensity_time_goal    TIME      -- yearly intensity minute goal 'HH:MM:SS.ffffff'
  steps                  INTEGER   -- total yearly steps
  steps_goal             INTEGER   -- yearly step goal
  floors                 FLOAT     -- total floors climbed
  floors_goal            FLOAT     -- yearly floor goal
  sleep_avg              TIME      -- average sleep duration 'HH:MM:SS.ffffff'
  sleep_min              TIME      -- minimum sleep duration 'HH:MM:SS.ffffff'
  sleep_max              TIME      -- maximum sleep duration 'HH:MM:SS.ffffff'
  rem_sleep_avg          TIME      -- average REM sleep 'HH:MM:SS.ffffff'
  rem_sleep_min          TIME      -- minimum REM sleep 'HH:MM:SS.ffffff'
  rem_sleep_max          TIME      -- maximum REM sleep 'HH:MM:SS.ffffff'
  stress_avg             FLOAT     -- average stress (0-100)
  calories_avg           FLOAT     -- average daily calories burned
  calories_bmr_avg       FLOAT     -- average basal metabolic rate calories
  calories_active_avg    FLOAT     -- average active calories
  calories_goal          INTEGER   -- yearly calorie goal
  calories_consumed_avg  FLOAT     -- average food calories logged
  activities             INTEGER   -- total number of activities
  activities_calories    INTEGER   -- total calories from activities
  activities_distance    FLOAT     -- total distance from activities (km)
  hydration_goal         INTEGER   -- yearly hydration goal (ml)
  hydration_avg          FLOAT     -- average daily hydration intake (ml)
  hydration_intake       INTEGER   -- total yearly hydration intake (ml)
  sweat_loss_avg         FLOAT     -- average daily sweat loss (ml)
  sweat_loss             INTEGER   -- total yearly sweat loss (ml)
  spo2_avg               FLOAT     -- average blood oxygen %
  spo2_min               FLOAT     -- minimum blood oxygen %
  rr_waking_avg          FLOAT     -- average waking respiration rate (breaths/min)
  rr_max                 FLOAT     -- maximum respiration rate
  rr_min                 FLOAT     -- minimum respiration rate
  bb_max                 FLOAT     -- body battery maximum (0-100)
  bb_min                 FLOAT     -- body battery minimum (0-100)
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
    "activity_monitoring": {
        "description": "Intraday activity log with detected activity type, intensity, distance, calories, steps, and elevation metrics at irregular timestamps throughout the day. Includes cumulative metrics for distance, active time, calories, steps, ascent, and descent.",
        "schema": ACTIVITY_MONITORING,
        "primary_db": "garmin_monitoring",
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
