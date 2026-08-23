from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Credentials(SQLModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserRead(SQLModel):
    id: int
    email: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ShoppingItemBase(SQLModel):
    name: str = Field(index=True, min_length=1, max_length=120)
    quantity: float = Field(default=1, gt=0, le=999)
    unit: str | None = Field(default=None, max_length=30)
    category: str = Field(default="Other", max_length=40)
    brand: str | None = Field(default=None, max_length=60)
    estimated_price: float | None = Field(default=None, ge=0)


class ShoppingItem(ShoppingItemBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    is_checked: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)


class ShoppingItemCreate(ShoppingItemBase):
    pass


class ShoppingItemUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    quantity: float | None = Field(default=None, gt=0, le=999)
    unit: str | None = Field(default=None, max_length=30)
    category: str | None = Field(default=None, max_length=40)
    brand: str | None = Field(default=None, max_length=60)
    estimated_price: float | None = Field(default=None, ge=0)
    is_checked: bool | None = None


class CommandRequest(SQLModel):
    transcript: str = Field(min_length=1, max_length=500)
    language: str = Field(default="en-US", max_length=20)


class CommandResponse(SQLModel):
    intent: str
    message: str
    item: ShoppingItem | None = None
    items: list[ShoppingItem] = []
    query: dict | None = None


class Suggestion(SQLModel):
    name: str
    reason: str
    category: str
    quantity: float = 1
    unit: str | None = None


class HistoryEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    item_name: str = Field(index=True)
    action: str = Field(default="added")
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)


class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    status: str = Field(default="placed", max_length=20)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrderLine(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    name: str = Field(max_length=120)
    quantity: float
    unit: str | None = Field(default=None, max_length=30)
    category: str = Field(max_length=40)
    brand: str | None = Field(default=None, max_length=60)
    estimated_price: float | None = None


class OrderLineRead(SQLModel):
    name: str
    quantity: float
    unit: str | None = None
    category: str
    brand: str | None = None
    estimated_price: float | None = None


class OrderRead(SQLModel):
    id: int
    status: str
    created_at: datetime
    items: list[OrderLineRead]


class OrderStatusUpdate(SQLModel):
    status: str = Field(min_length=1, max_length=20)
