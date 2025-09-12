from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional, Union


# object schemas

# for JWTs:
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str



# for users:
class UserBase(BaseModel):
    username: str = Field(min_length=4, max_length=100)
    email: Optional[str] = Field(default=None)
    full_name: Optional[str] = Field(default=None)


class UserCreate(UserBase):  # to be used for creating an user in the DB
    # TODO: change the min length when you're further along in dev
    password: str = Field(min_length=4)


class UserInDB(UserBase):   # to be used when the user is stored in the DB
    id: str = Field(default_factory=lambda: uuid4().hex,
                    description="User ID (UUID hex)")
    hashed_password: str


class User(UserBase):   # to be returned to the client (NOTE: should NEVER include password)
    id: str
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

    id: str = Field(default_factory=lambda: uuid4().hex,
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
class StatusResponse(BaseModel):
    """GET /status/{project_id} response."""
    project_id: str
    status: Status = Field(description="Current status of analysis")
    result: Optional[AnalysisResult] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now())

    # example responses (from tests/conftest.py):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "776eaf11601c429783d23248b361d2b8",
                    "status": "completed",
                    "result": {
                        "project_name": "MyCoolCompleteProject",
                        "analysis_date": str(date.today()),
                        "files": [
                            {"name": "contourpy", "version": "1.3.1",
                             "license": "BSD-3-Clause", "confidence_score": 0.80},
                            {"name": "contourpy", "version": "1.3.1",
                             "license": "BSD-3-Clause", "confidence_score": 0.80}
                        ]
                    }
                },
                {
                    "id": "9c2a06a435814724a8994ec9b48ff4cd",
                    "status": "failed",
                    "result": None
                }
            ]
        }
    }


class AnalyzeResponse(BaseModel):
    """
    POST /analyze response. Status will be "IN_PROGRESS" when there's no result yet, or "FAILED"/"COMPLETED" when there's a result.
    """
    project_id: str
    status: Status
    result: Optional[AnalysisResult] = None

    # example responses (from tests/conftest.py):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "d1216a154352495db55d136982ebe475",
                    "status": Status.IN_PROGRESS,
                    "result": None
                }
            ]
        }
    }


# REST response schemas (deprecated)
class LlmPrompt(BaseModel):
    text: str


class LlmResponse(BaseModel):
    text: str


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

class EventRecord(BaseModel):
    """
    Represents a single event log in the database.
    """
    user_id: str = Field(description="ID of the user who initiated the event")
    project_name: str = Field(description="Project name")
    event: EventType = Field(description="Type of event that occurred")
    timestamp: datetime = Field(default_factory=datetime.now)
    # content can be the requirements.txt file (str), the analysis result, or None
    content: Optional[Union[str, AnalysisResult]] = None
