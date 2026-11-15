from typing import Literal, Optional
from pydantic import BaseModel, Field, AliasChoices


class MedicalRecord(BaseModel):
    patient_reference: str = Field(
        ..., min_length=1,
        description="Username of the user / patient reference",
        validation_alias=AliasChoices("patient_reference", "username")
    )

    medical_system: Literal[
        "allopathy",
        "ayurveda",
        "homeopathy"
    ]

    record_type: Literal[
        "prescription",
        "ehr"
    ]

    condition_terms: list[str] = Field(default_factory=list)

    medicines: list[str] = Field(default_factory=list)

    notes: Optional[str] = None

    comments: Optional[str] = Field(
        default=None,
        description="Patient or user comments, experience, and opinion regarding this prescription for doctor review"
    )


class RecordCommentUpdate(BaseModel):
    comments: Optional[str] = Field(
        default=None,
        description="User or patient opinion/feedback regarding the prescription"
    )


class TermExplainRequest(BaseModel):
    term: str = Field(..., min_length=1, description="Medical term or code to explain")


class GoogleAuthRequest(BaseModel):
    credential: Optional[str] = Field(default=None, description="Google OAuth ID Token JWT")
    username: Optional[str] = Field(default=None, description="User's full name / username")
    email: Optional[str] = Field(default=None, description="User's mandatory Gmail / Google email address")
    password: Optional[str] = Field(default=None, description="User's mandatory password")
    picture: Optional[str] = Field(default=None, description="Google profile picture URL")


