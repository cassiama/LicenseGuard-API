from uuid import uuid4, UUID
from enum import Enum
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import List, Optional, Union
from sqlmodel import SQLModel, Field


# object schemas

# for JWTs:
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str


# for users:
class UserBase(SQLModel):
    username: str = Field(min_length=4, max_length=100, index=True)
    email: Optional[str] = Field(default=None)
    full_name: Optional[str] = Field(default=None)


class UserCreate(UserBase):  # to be used for creating an user in the DB
    # TODO: change the min length when you're further along in dev
    password: str = Field(min_length=4)


class User(UserBase, table=True):   # to be used when the user is stored in the DB
    id: UUID = Field(default_factory=uuid4,
                     description="User ID (UUID hex)", primary_key=True)
    hashed_password: str


# to be returned to the client (NOTE: should NEVER include password)
class UserPublic(UserBase):
    id: UUID
    # this allows the model to be created from ORM objects (like SQLAlchemy)

    class ConfigDict:
        from_attributes = True


# for analysis results:
class Status(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(BaseModel):
    """Represents a single analysis project."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4,
                     description="Project ID (UUID hex)")
    name: str = Field(min_length=1, max_length=100)


class DependencyReport(BaseModel):
    """AI agent output for a single project dependency."""
    name: str = Field(min_length=2, max_length=200)
    version: str = Field(min_length=1, max_length=80)
    # all licenses must come from the SPDX database
    license: str = Field(min_length=2, max_length=100)
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Ranges from 0.0 to 1.0 (inclusive)")


# OpenAI / LLM schemas
class AnalysisResult(BaseModel):
    """Top-level AI agent output (per-file results)."""
    project_name: str
    analysis_date: date
    files: list[DependencyReport]


# REST response schemas
class AnalyzeResponse(BaseModel):
    """
    POST /analyze response. Status will be "IN_PROGRESS" when there's no result yet, or "FAILED"/"COMPLETED" when there's a result.
    """
    project_id: UUID
    status: Status
    result: Optional[AnalysisResult] = None

    # example responses (from tests/conftest.py):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "93fe969a-c0fc-4c01-8b92-b866927c552f",
                    "status": "completed",
                    "result": {
                        "analysis_date": "2025-08-30",
                        "files": [
                            {
                                "confidence_score": 0.8,
                                "license": "BSD-3-Clause",
                                "name": "contourpy",
                                "version": "1.3.1"
                            },
                            {
                                "confidence_score": 0.8,
                                "license": "BSD-3-Clause",
                                "name": "contourpy",
                                "version": "1.3.1"
                            }
                        ],
                        "project_name": "MyCoolCompleteProject"
                    }
                },
                {
                    "id": "8fd82d6c-911d-4932-9d38-02fbadeace22",
                    "status": "failed",
                    "result": None
                }
            ]
        }
    }


# internal schemas
# DB persistence records
class EventType(str, Enum):
    """Enumeration for the types of events that can be logged."""
    PROJECT_CREATED = "PROJECT_CREATED"
    VALIDATION_FAILED = "DEPENDENCY_VALIDATION_FAILED"
    VALIDATION_SUCCESS = "DEPENDENCY_VALIDATION_SUCCESS"
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"


class Event(SQLModel, table=True):
    """
    Represents a single event log in the database.
    """
    id: UUID = Field(default_factory=uuid4,
                     description="ID of the event", primary_key=True)
    user_id: UUID = Field(
        description="ID of the user who initiated the event", foreign_key="user.id")
    project_name: str = Field(description="Project name", index=True)
    event: EventType = Field(description="Type of event that occurred")
    timestamp: datetime = Field(default_factory=datetime.now)
    # content can be a string (potential values: the requirements.txt file, the requirements
    # themselves, or the analysis result), or None
    content: Optional[str] = None
