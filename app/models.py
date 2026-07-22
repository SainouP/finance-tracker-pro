from datetime import date, datetime, timezone
from enum import Enum
from sqlmodel import Field, SQLModel

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class TransactionType(str, Enum):
    INCOME = "Ingreso"
    EXPENSE = "Gasto"

class PaymentMethod(str, Enum):
    CASH = "Efectivo"
    CARD = "Tarjeta"
    TRANSFER = "Transferencia"
    YAPE = "Yape"
    PLIN = "Plin"
    OTHER = "Otro"

class Category(str, Enum):
    SALARY = "Sueldo"
    FREELANCE = "Freelance"
    FOOD = "Comida"
    TRANSPORT = "Transporte"
    HEALTH = "Salud"
    ENTERTAINMENT = "Entretenimiento"
    EDUCATION = "Educación"
    HOME = "Hogar"
    SERVICES = "Servicios"
    SHOPPING = "Compras"
    SAVINGS = "Ahorro"
    OTHER = "Otros"

class InsightType(str, Enum):
    SAVINGS = "Ahorro"
    ALERT = "Alerta"
    TREND = "Tendencia"
    GOAL = "Meta"
    BUDGET = "Presupuesto"
    PAYMENT = "Pago"

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(unique=True, index=True, max_length=150)
    password_hash: str
    currency: str = Field(default="PEN", max_length=10)
    monthly_income_target: float = Field(default=0, ge=0)
    financial_goal: str | None = Field(default=None, max_length=250)
    created_at: datetime = Field(default_factory=utc_now)

class Transaction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    transaction_type: TransactionType
    category: Category
    amount: float = Field(gt=0)
    description: str = Field(min_length=2, max_length=250)
    payment_method: PaymentMethod = Field(default=PaymentMethod.OTHER)
    transaction_date: date = Field(default_factory=date.today, index=True)
    created_at: datetime = Field(default_factory=utc_now)

class Budget(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    category: Category
    monthly_limit: float = Field(gt=0)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2020, le=2100)
    created_at: datetime = Field(default_factory=utc_now)

class SavingsGoal(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(min_length=2, max_length=120)
    target_amount: float = Field(gt=0)
    current_amount: float = Field(default=0, ge=0)
    target_date: date | None = None
    created_at: datetime = Field(default_factory=utc_now)

class RecurringExpense(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(min_length=2, max_length=120)
    category: Category
    amount: float = Field(gt=0)
    due_day: int = Field(ge=1, le=31)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)

class RecurringPayment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    recurring_id: int = Field(foreign_key="recurringexpense.id", index=True)
    transaction_id: int = Field(foreign_key="transaction.id")
    month: int = Field(ge=1, le=12, index=True)
    year: int = Field(ge=2020, le=2100, index=True)
    paid_at: datetime = Field(default_factory=utc_now)

class FinancialInsight(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    insight_type: InsightType
    title: str = Field(max_length=120)
    message: str = Field(max_length=400)
    event_key: str = Field(max_length=200, index=True)
    is_reviewed: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)

class LoginRequest(SQLModel):
    email: str
    password: str

class RegisterRequest(SQLModel):
    full_name: str
    email: str
    password: str

class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    user_name: str

class TransactionCreate(SQLModel):
    transaction_type: TransactionType
    category: Category
    amount: float
    description: str
    payment_method: PaymentMethod = PaymentMethod.OTHER
    transaction_date: date = Field(default_factory=date.today)

class BudgetCreate(SQLModel):
    category: Category
    monthly_limit: float
    month: int
    year: int

class GoalCreate(SQLModel):
    name: str
    target_amount: float
    current_amount: float = 0
    target_date: date | None = None

class GoalContribution(SQLModel):
    amount: float

class RecurringCreate(SQLModel):
    name: str
    category: Category
    amount: float
    due_day: int
