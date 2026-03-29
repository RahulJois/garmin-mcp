"""Pytest fixtures and configuration for garmin-mcp tests."""

import sqlite3
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Create a temporary SQLite database for testing.
    
    Yields:
        Path to temporary database file as string.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_sleep_db(temp_db: str) -> str:
    """Create a sample sleep database with test data.
    
    Args:
        temp_db: Path to temporary database.
        
    Returns:
        Path to sample database.
    """
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE sleep (
            id INTEGER PRIMARY KEY,
            day TEXT,
            start_time TEXT,
            end_time TEXT,
            total_sleep_seconds INTEGER,
            deep_sleep_seconds INTEGER,
            light_sleep_seconds INTEGER,
            rem_sleep_seconds INTEGER
        )
    """)
    
    cursor.execute("""
        INSERT INTO sleep VALUES
        (1, '2026-03-20', '2026-03-19 22:00:00', '2026-03-20 06:00:00', 28800, 7200, 14400, 7200),
        (2, '2026-03-21', '2026-03-20 22:30:00', '2026-03-21 06:15:00', 27900, 6900, 14100, 6900),
        (3, '2026-03-22', '2026-03-21 23:00:00', '2026-03-22 07:00:00', 28800, 7200, 14400, 7200)
    """)
    
    conn.commit()
    conn.close()
    
    return temp_db


@pytest.fixture
def sample_heart_rate_db(temp_db: str) -> str:
    """Create a sample heart rate database with test data.
    
    Args:
        temp_db: Path to temporary database.
        
    Returns:
        Path to sample database.
    """
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE heart_rate (
            id INTEGER PRIMARY KEY,
            day TEXT,
            resting_heart_rate INTEGER,
            min_heart_rate INTEGER,
            max_heart_rate INTEGER
        )
    """)
    
    cursor.execute("""
        INSERT INTO heart_rate VALUES
        (1, '2026-03-20', 45, 38, 168),
        (2, '2026-03-21', 48, 40, 175),
        (3, '2026-03-22', 46, 39, 170)
    """)
    
    conn.commit()
    conn.close()
    
    return temp_db
