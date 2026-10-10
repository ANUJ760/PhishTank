"""Pydantic request and response schemas for the FastAPI HTTP adapter."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, EmailStr, Field
from backend.models import Conflict

class UserSignUpRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=150)
    password: str = Field(..., min_length=6, max_length=100)

class UserSignInRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)

class TextIntakeRequest(BaseModel):
    text: str = Field(..., min_length=1)

class SolveRequest(BaseModel):
    minimal_change: bool = True

class ExplainConflictRequest(BaseModel):
    conflict: Conflict

class ApproveOptionRequest(BaseModel):
    as_user: str

class EditRuleRequest(BaseModel):
    params: dict | None = None
    owner: str | None = None

class ScoreboardRequest(BaseModel):
    runs: int = Field(5, ge=1, le=10)

class DashboardSummaryResponse(BaseModel):
    confirmed_rules_count: int
    draft_rules_count: int
    conflict_active: bool
    conflict_rule_ids: list[str]
    scheduled_sessions_count: int
    published_version: int | None
    latest_schedule_hash: str | None
    system_healthy: bool


# -------------------------------------------------------------------------
# ReliefOps Request Schemas
# -------------------------------------------------------------------------

class ReliefOptimizeRequest(BaseModel):
    scenario_id: str = "SCENARIO-MAIN"
    scenario_name: str = "Optimal CP-SAT Disaster Allocation"


class ReliefSimulateRequest(BaseModel):
    delta: dict = Field(default_factory=dict)
    scenario_id: str | None = None
    scenario_name: str = "What-If Counterfactual"


class ReliefApproveRequest(BaseModel):
    plan_id: str
    approved_by: str
    notes: str = "Approved by commander"


class ReliefDispatchIntakeRequest(BaseModel):
    text: str = Field(..., min_length=5)


class ReliefExplainRequest(BaseModel):
    plan_id: str | None = None

