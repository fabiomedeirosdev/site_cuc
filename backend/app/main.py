from typing import Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from app.config import settings


PlanId = Literal["associado-a", "associado-b", "associado-c"]


class CheckoutRequest(BaseModel):
    plan_id: PlanId
    email: EmailStr


class RegistrationRequest(BaseModel):
    token: str
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


PLANS = {
    "associado-a": {"name": "Associado A", "amount": 12000},
    "associado-b": {"name": "Associado B", "amount": 6500},
    "associado-c": {"name": "Associado C", "amount": 3500},
}

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/api/plans")
def list_plans() -> dict[str, dict[str, str | int]]:
    return PLANS


@app.post("/api/checkout", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def create_checkout(payload: CheckoutRequest) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Checkout PagSeguro ainda não configurado. "
            "A integração deve ser implementada no backend."
        ),
    )


@app.post("/api/webhooks/pagseguro", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def pagseguro_webhook() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Webhook PagSeguro ainda não configurado.",
    )


@app.post("/api/auth/complete-registration", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def complete_registration(payload: RegistrationRequest) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Cadastro privado ainda depende de banco e validação de token.",
    )


@app.post("/api/auth/login", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def login(payload: LoginRequest) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Login ainda depende da implementação de usuários e sessões.",
    )
