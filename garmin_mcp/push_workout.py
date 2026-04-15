"""
Garmin Connect workout push logic.

Provides:
  - get_garmin_client()      : authenticated Garmin Connect client
  - build_running_workout()  : construct a RunningWorkout from a steps spec
  - PUSH_WORKOUT_TOOL        : MCP tool definition for push_workout
  - handle_push_workout()    : MCP tool handler
"""

import logging
from pathlib import Path
from typing import Any

import mcp.types as types

from . import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_garmin_client():
    """Return an authenticated Garmin Connect client.

    On first run (no token dir) reads credentials from
    ~/.GarminDb/GarminConnectConfig.json (or GARMIN_EMAIL / GARMIN_PASSWORD
    env vars) and saves OAuth tokens to GARMIN_TOKEN_DIR for silent reuse.
    On subsequent runs loads the saved tokens with no credentials needed.
    If saved tokens are stale, falls back to credentials and re-saves.
    """
    import garminconnect

    token_dir = config.GARMIN_TOKEN_DIR
    tokens_exist = Path(token_dir).is_dir()

    if tokens_exist:
        email, password = None, None
    else:
        email, password = config.get_garmin_credentials()

    client = garminconnect.Garmin(email=email, password=password)

    try:
        client.login(tokenstore=token_dir)
    except garminconnect.GarminConnectAuthenticationError as exc:
        if not tokens_exist:
            raise RuntimeError(
                "Authentication failed. Check credentials in "
                f"{config.GARMIN_CONNECT_CONFIG} or set GARMIN_EMAIL / "
                f"GARMIN_PASSWORD environment variables. Error: {exc}"
            ) from exc
        # Saved tokens are stale — retry with credentials
        email, password = config.get_garmin_credentials()
        if not email or not password:
            raise RuntimeError(
                "Saved tokens are invalid/expired. Add credentials to "
                f"{config.GARMIN_CONNECT_CONFIG} or set GARMIN_EMAIL / "
                f"GARMIN_PASSWORD environment variables. Error: {exc}"
            ) from exc
        client = garminconnect.Garmin(email=email, password=password)
        client.login(tokenstore=token_dir)

    return client


# ---------------------------------------------------------------------------
# Pace helpers
# ---------------------------------------------------------------------------

def _parse_pace(pace_str: str) -> float:
    """Convert 'M:SS' (min:sec per km) to meters/second."""
    parts = pace_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid pace format '{pace_str}'. Expected 'M:SS' (e.g. '4:21')."
        )
    minutes, seconds = int(parts[0]), int(parts[1])
    secs_per_km = minutes * 60 + seconds
    if secs_per_km <= 0:
        raise ValueError(f"Pace must be positive, got '{pace_str}'.")
    return 1000.0 / secs_per_km  # m/s


def _pace_target(pace_mps: float) -> tuple[dict[str, Any], float, float]:
    """Return (targetType dict, low_mps, high_mps) for a ±5 s/km speed-zone target.

    targetValueOne/targetValueTwo must be top-level fields on the ExecutableStep,
    NOT nested inside targetType — Garmin silently ignores values inside targetType.
    The correct key for a speed/pace zone is "speed.zone" (workoutTargetTypeId 6).
    """
    secs_per_km = 1000.0 / pace_mps
    low_mps = 1000.0 / (secs_per_km + 5)
    high_mps = 1000.0 / (secs_per_km - 5) if secs_per_km > 5 else pace_mps * 1.05
    target_type = {
        "workoutTargetTypeId": 6,  # speed.zone
        "workoutTargetTypeKey": "speed.zone",
        "displayOrder": 6,
    }
    return target_type, low_mps, high_mps


# ---------------------------------------------------------------------------
# Step builder
# ---------------------------------------------------------------------------

_NO_TARGET: dict[str, Any] = {
    "workoutTargetTypeId": 1,
    "workoutTargetTypeKey": "no.target",
    "displayOrder": 1,
}

VALID_STEP_TYPES = {"warmup", "cooldown", "interval", "recovery", "repeat"}


def _build_steps(steps: list, base_order: int = 1) -> tuple[list, int]:
    """Recursively convert a steps spec list into garminconnect workout objects.

    Returns (built_steps, next_available_order).
    """
    from garminconnect.workout import (
        ConditionType,
        ExecutableStep,
        StepType,
        create_repeat_group,
    )

    _STEP_TYPE_ID = {
        "warmup":   StepType.WARMUP,
        "cooldown": StepType.COOLDOWN,
        "interval": StepType.INTERVAL,
        "recovery": StepType.RECOVERY,
    }

    built: list = []
    order = base_order

    for raw in steps:
        step_type = raw.get("type", "").lower()
        if step_type not in VALID_STEP_TYPES:
            raise ValueError(
                f"Invalid step type '{step_type}'. "
                f"Must be one of: {sorted(VALID_STEP_TYPES)}."
            )

        if step_type == "repeat":
            reps = raw.get("reps")
            if not isinstance(reps, int) or reps < 1:
                raise ValueError(
                    "'repeat' step requires a positive integer 'reps' field."
                )
            sub_raw = raw.get("steps")
            if not isinstance(sub_raw, list) or not sub_raw:
                raise ValueError(
                    "'repeat' step requires a non-empty 'steps' list."
                )
            inner, order = _build_steps(sub_raw, base_order=order)
            built.append(create_repeat_group(
                iterations=reps,
                workout_steps=inner,
                step_order=order,
            ))
            order += 1
            continue

        # --- Pace target (if any) ---
        # targetValueOne/Two MUST be top-level fields on ExecutableStep.
        # Garmin silently ignores them when nested inside targetType.
        pace_str = raw.get("target_pace_min_per_km")
        if pace_str:
            target_type, low_mps, high_mps = _pace_target(_parse_pace(pace_str))
        else:
            target_type, low_mps, high_mps = _NO_TARGET, None, None

        # --- End condition ---
        if "distance_km" in raw:
            end_condition = {
                "conditionTypeId": ConditionType.DISTANCE,
                "conditionTypeKey": "distance",
                "displayOrder": 1,
                "displayable": True,
            }
            end_value = float(raw["distance_km"]) * 1000.0
        elif "duration_secs" in raw:
            end_condition = {
                "conditionTypeId": ConditionType.TIME,
                "conditionTypeKey": "time",
                "displayOrder": 2,
                "displayable": True,
            }
            end_value = float(raw["duration_secs"])
        else:
            raise ValueError(
                f"Step type '{step_type}' requires either "
                "'duration_secs' or 'distance_km'."
            )

        # Always build ExecutableStep directly so we control the top-level layout.
        extra: dict[str, Any] = {}
        if low_mps is not None:
            extra["targetValueOne"] = low_mps
            extra["targetValueTwo"] = high_mps

        built.append(ExecutableStep(
            stepOrder=order,
            stepType={
                "stepTypeId": _STEP_TYPE_ID[step_type],
                "stepTypeKey": step_type,
                "displayOrder": 3,
            },
            endCondition=end_condition,
            endConditionValue=end_value,
            targetType=target_type,
            **extra,
        ))
        order += 1

    return built, order


def _estimate_duration(steps: list) -> int:
    """Rough total-duration estimate (seconds) used as workout metadata."""
    total = 0
    for s in steps:
        if s.get("type") == "repeat":
            total += _estimate_duration(s.get("steps", [])) * s.get("reps", 1)
        elif "duration_secs" in s:
            total += int(s["duration_secs"])
        elif "distance_km" in s:
            total += int(s["distance_km"] * 300)  # ~5 min/km estimate
    return total


def build_running_workout(name: str, steps: list):
    """Construct a RunningWorkout from a steps spec list."""
    from garminconnect.workout import RunningWorkout, WorkoutSegment

    built_steps, _ = _build_steps(steps, base_order=1)
    segment = WorkoutSegment(
        segmentOrder=1,
        sportType={"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
        workoutSteps=built_steps,
    )
    return RunningWorkout(
        workoutName=name,
        estimatedDurationInSecs=_estimate_duration(steps),
        workoutSegments=[segment],
    )


# ---------------------------------------------------------------------------
# MCP tool definition
# ---------------------------------------------------------------------------

PUSH_WORKOUT_TOOL = types.Tool(
    name="push_workout",
    description=(
        "Push a structured running workout to Garmin Connect and optionally "
        "schedule it on the Garmin calendar. "
        "Supports warmup, cooldown, interval, recovery, and nested repeat steps. "
        "Steps can be time-based (duration_secs) or distance-based (distance_km). "
        "An optional target_pace_min_per_km (e.g. '4:21') can be added to any step. "
        "Returns the workout_id, scheduled_date, and a direct Garmin Connect URL."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Workout name shown on the watch and in Garmin Connect.",
            },
            "date": {
                "type": "string",
                "description": (
                    "Optional YYYY-MM-DD date to schedule on the Garmin calendar. "
                    "If omitted, the workout is uploaded to the library only."
                ),
            },
            "steps": {
                "type": "array",
                "description": (
                    "Ordered list of workout steps. Each step must have a 'type' "
                    "('warmup', 'cooldown', 'interval', 'recovery', or 'repeat'). "
                    "Non-repeat steps need either 'duration_secs' or 'distance_km'. "
                    "Optional 'target_pace_min_per_km' (e.g. '4:21') sets a pace target. "
                    "A 'repeat' step needs 'reps' (int) and 'steps' (nested step list)."
                ),
                "items": {"type": "object"},
                "minItems": 1,
            },
        },
        "required": ["name", "steps"],
    },
)


# ---------------------------------------------------------------------------
# MCP tool handler
# ---------------------------------------------------------------------------

def handle_push_workout(arguments: dict) -> dict[str, Any]:
    """Execute the push_workout tool. Returns a result dict (not MCP-wrapped)."""
    name = arguments.get("name", "").strip()
    date = arguments.get("date", "").strip() or None
    steps = arguments.get("steps")

    if not name:
        return {"error": "'name' is required."}
    if not isinstance(steps, list) or not steps:
        return {"error": "'steps' must be a non-empty list."}

    logger.info(f"push_workout: name='{name}' date={date}")

    try:
        workout = build_running_workout(name, steps)
    except ValueError as exc:
        return {"error": f"Invalid workout spec: {exc}"}

    try:
        garmin = get_garmin_client()
    except RuntimeError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": f"Authentication error: {exc}"}

    try:
        result = garmin.upload_running_workout(workout)
        logger.debug(f"upload_running_workout response: {result}")
    except Exception as exc:
        return {"error": f"Garmin API error during upload: {exc}"}

    # API may return a list or a dict
    if isinstance(result, list) and result:
        result = result[0]
    workout_id = (
        result.get("workoutId")
        or result.get("workout", {}).get("workoutId")
    )
    connect_url = (
        f"https://connect.garmin.com/modern/workout/{workout_id}"
        if workout_id else None
    )

    if date and workout_id:
        try:
            garmin.schedule_workout(workout_id, date)
            logger.info(f"push_workout: scheduled {workout_id} on {date}")
        except Exception as exc:
            logger.warning(f"push_workout: schedule failed: {exc}")
            return {
                "workout_id": str(workout_id),
                "scheduled_date": None,
                "warning": f"Workout uploaded but scheduling failed: {exc}",
                "garmin_connect_url": connect_url,
            }

    return {
        "workout_id": str(workout_id) if workout_id else None,
        "scheduled_date": date if (date and workout_id) else None,
        "garmin_connect_url": connect_url,
    }
