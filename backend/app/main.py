from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from .database import create_db_and_tables, get_session
from .models import (
    CommandRequest,
    CommandResponse,
    Credentials,
    HistoryEvent,
    Order,
    OrderLine,
    OrderLineRead,
    OrderRead,
    OrderStatusUpdate,
    ShoppingItem,
    ShoppingItemCreate,
    ShoppingItemUpdate,
    Suggestion,
    TokenResponse,
    User,
    UserRead,
)
from .services import (
    build_suggestions,
    categorise,
    groq_parse,
    parse_command,
    seed_history,
)
from .settings import get_settings


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


# ============================================================
# FASTAPI APP
# ============================================================

settings = get_settings()

app = FastAPI(
    title="Voice Cart API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.allowed_origins.split(",")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ORDER HELPERS
# ============================================================

def order_read(order: Order, session: Session) -> OrderRead:
    lines = session.exec(
        select(OrderLine).where(
            OrderLine.order_id == order.id
        )
    ).all()

    return OrderRead(
        id=order.id,
        status=order.status,
        created_at=order.created_at,
        items=[
            OrderLineRead(**line.model_dump())
            for line in lines
        ],
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "groq_enabled": bool(settings.groq_api_key),
        "auth_enabled": True,
    }


# ============================================================
# AUTHENTICATION
# ============================================================

@app.post(
    "/api/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: Credentials,
    session: Session = Depends(get_session),
):
    email = payload.email.strip().lower()

    if "@" not in email:
        raise HTTPException(
            422,
            "Enter a valid email address.",
        )

    existing_user = session.exec(
        select(User).where(User.email == email)
    ).first()

    if existing_user:
        raise HTTPException(
            409,
            "An account with that email already exists.",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    seed_history(session, user.id)

    return TokenResponse(
        access_token=create_access_token(user),
        user=UserRead(
            id=user.id,
            email=user.email,
        ),
    )


@app.post(
    "/api/auth/login",
    response_model=TokenResponse,
)
def login(
    payload: Credentials,
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(
            User.email == payload.email.strip().lower()
        )
    ).first()

    if not user or not verify_password(
        payload.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Email or password is incorrect.",
        )

    return TokenResponse(
        access_token=create_access_token(user),
        user=UserRead(
            id=user.id,
            email=user.email,
        ),
    )


@app.get(
    "/api/auth/me",
    response_model=UserRead,
)
def me(
    user: User = Depends(get_current_user),
):
    return UserRead(
        id=user.id,
        email=user.email,
    )


# ============================================================
# SHOPPING ITEMS
# ============================================================

@app.get(
    "/api/items",
    response_model=list[ShoppingItem],
)
def get_items(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return session.exec(
        select(ShoppingItem)
        .where(
            ShoppingItem.user_id == user.id
        )
        .order_by(
            ShoppingItem.is_checked,
            ShoppingItem.created_at.desc(),
        )
    ).all()


@app.post(
    "/api/items",
    response_model=ShoppingItem,
    status_code=status.HTTP_201_CREATED,
)
def create_item(
    payload: ShoppingItemCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    # Convert Pydantic/SQLModel payload into a dictionary.
    data = payload.model_dump()

    # Automatically categorise the item if the user
    # did not explicitly provide a category.
    data["category"] = (
        payload.category
        or categorise(payload.name)
    )

    # Associate the item with the logged-in user.
    data["user_id"] = user.id

    # IMPORTANT:
    # Do not pass category separately here because it
    # already exists inside data.
    item = ShoppingItem(**data)

    session.add(item)

    session.add(
        HistoryEvent(
            item_name=item.name,
            user_id=user.id,
        )
    )

    session.commit()
    session.refresh(item)

    return item


def get_user_item(
    item_id: int,
    session: Session,
    user: User,
) -> ShoppingItem:
    item = session.get(
        ShoppingItem,
        item_id,
    )

    if not item or item.user_id != user.id:
        raise HTTPException(
            404,
            "Item not found",
        )

    return item


@app.patch(
    "/api/items/{item_id}",
    response_model=ShoppingItem,
)
def update_item(
    item_id: int,
    payload: ShoppingItemUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = get_user_item(
        item_id,
        session,
        user,
    )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(item, key, value)

    # If the item name changes but the user does not
    # explicitly provide a category, recategorise it.
    if payload.name and not payload.category:
        item.category = categorise(
            payload.name
        )

    session.add(item)
    session.commit()
    session.refresh(item)

    return item


@app.delete(
    "/api/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_item(
    item_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = get_user_item(
        item_id,
        session,
        user,
    )

    session.delete(item)
    session.commit()


@app.delete(
    "/api/items",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_items(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    items = session.exec(
        select(ShoppingItem).where(
            ShoppingItem.user_id == user.id
        )
    ).all()

    for item in items:
        session.delete(item)

    session.commit()


# ============================================================
# SUGGESTIONS
# ============================================================

@app.get(
    "/api/suggestions",
    response_model=list[Suggestion],
)
def suggestions(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return build_suggestions(
        session,
        user.id,
    )


# ============================================================
# SEARCH
# ============================================================

@app.get(
    "/api/search",
    response_model=list[ShoppingItem],
)
def search_items(
    q: str = Query(min_length=1),
    max_price: float | None = None,
    brand: str | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    query = select(ShoppingItem).where(
        ShoppingItem.user_id == user.id,
        ShoppingItem.name.ilike(f"%{q}%"),
    )

    if max_price is not None:
        query = query.where(
            ShoppingItem.estimated_price <= max_price
        )

    if brand:
        query = query.where(
            ShoppingItem.brand.ilike(f"%{brand}%")
        )

    return session.exec(query).all()


# ============================================================
# ORDERS
# ============================================================

@app.post(
    "/api/orders",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
def place_order(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    items = session.exec(
        select(ShoppingItem).where(
            ShoppingItem.user_id == user.id,
            ShoppingItem.is_checked == False,  # noqa: E712
        )
    ).all()

    if not items:
        raise HTTPException(
            400,
            "Add an unpurchased item before placing an order.",
        )

    order = Order(
        user_id=user.id,
        status="placed",
    )

    session.add(order)
    session.flush()

    for item in items:
        session.add(
            OrderLine(
                order_id=order.id,
                name=item.name,
                quantity=item.quantity,
                unit=item.unit,
                category=item.category,
                brand=item.brand,
                estimated_price=item.estimated_price,
            )
        )

        session.add(
            HistoryEvent(
                item_name=item.name,
                action="ordered",
                user_id=user.id,
            )
        )

        session.delete(item)

    session.commit()
    session.refresh(order)

    return order_read(
        order,
        session,
    )


@app.get(
    "/api/orders",
    response_model=list[OrderRead],
)
def get_orders(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    orders = session.exec(
        select(Order)
        .where(
            Order.user_id == user.id
        )
        .order_by(
            Order.created_at.desc()
        )
    ).all()

    return [
        order_read(order, session)
        for order in orders
    ]


@app.patch(
    "/api/orders/{order_id}",
    response_model=OrderRead,
)
def update_order(
    order_id: int,
    payload: OrderStatusUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    order = session.get(
        Order,
        order_id,
    )

    if not order or order.user_id != user.id:
        raise HTTPException(
            404,
            "Order not found",
        )

    if payload.status not in {
        "placed",
        "delivered",
        "cancelled",
    }:
        raise HTTPException(
            422,
            "Status must be placed, delivered, or cancelled.",
        )

    order.status = payload.status

    session.add(order)
    session.commit()
    session.refresh(order)

    return order_read(
        order,
        session,
    )


# ============================================================
# VOICE / NATURAL LANGUAGE COMMANDS
# ============================================================

@app.post(
    "/api/command",
    response_model=CommandResponse,
)
async def run_command(
    payload: CommandRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    # First try Groq/NLP parsing.
    # If unavailable, fall back to local command parsing.
    command = (
        await groq_parse(
            payload.transcript,
            payload.language,
        )
        or parse_command(
            payload.transcript,
            payload.language,
        )
    )

    # --------------------------------------------------------
    # ADD COMMAND
    # --------------------------------------------------------

    if command.intent == "add":
        if not command.name:
            return CommandResponse(
                intent="add",
                message=(
                    "I didn't catch the item. "
                    "Please try again."
                ),
            )

        existing = session.exec(
            select(ShoppingItem).where(
                ShoppingItem.user_id == user.id,
                ShoppingItem.name.ilike(
                    command.name
                ),
            )
        ).first()

        if existing:
            existing.quantity += command.quantity

            session.add(existing)

            item = existing

            message = (
                f"Updated {item.name} "
                f"to {item.quantity:g}."
            )

        else:
            item = ShoppingItem(
                name=command.name,
                quantity=command.quantity,
                unit=command.unit,
                category=categorise(
                    command.name
                ),
                user_id=user.id,
            )

            session.add(item)

            message = (
                f"Added {item.quantity:g} "
                f"{item.unit or ''} "
                f"{item.name}."
            ).replace("  ", " ")

        session.add(
            HistoryEvent(
                item_name=item.name,
                user_id=user.id,
            )
        )

        session.commit()
        session.refresh(item)

        return CommandResponse(
            intent="add",
            message=message,
            item=item,
        )

    # --------------------------------------------------------
    # REMOVE COMMAND
    # --------------------------------------------------------

    if command.intent == "remove":
        item = session.exec(
            select(ShoppingItem).where(
                ShoppingItem.user_id == user.id,
                ShoppingItem.name.ilike(
                    command.name or ""
                ),
            )
        ).first()

        if not item:
            return CommandResponse(
                intent="remove",
                message=(
                    f"I couldn't find "
                    f"{command.name or 'that item'} "
                    f"on your list."
                ),
            )

        name = item.name

        session.delete(item)
        session.commit()

        return CommandResponse(
            intent="remove",
            message=f"Removed {name}.",
        )

    # --------------------------------------------------------
    # CLEAR COMMAND
    # --------------------------------------------------------

    if command.intent == "clear":
        items = session.exec(
            select(ShoppingItem).where(
                ShoppingItem.user_id == user.id
            )
        ).all()

        for item in items:
            session.delete(item)

        session.commit()

        return CommandResponse(
            intent="clear",
            message="Your shopping list is clear.",
        )

    # --------------------------------------------------------
    # LIST COMMAND
    # --------------------------------------------------------

    if command.intent == "list":
        items = session.exec(
            select(ShoppingItem).where(
                ShoppingItem.user_id == user.id,
                ShoppingItem.is_checked == False,  # noqa: E712
            )
        ).all()

        return CommandResponse(
            intent="list",
            message=(
                f"You have {len(items)} "
                f"item{'s' if len(items) != 1 else ''} left."
            ),
            items=items,
        )

    # --------------------------------------------------------
    # SEARCH COMMAND
    # --------------------------------------------------------

    results = search_items(
        command.name or payload.transcript,
        command.max_price,
        command.brand,
        session,
        user,
    )

    return CommandResponse(
        intent="search",
        message=(
            f"Found {len(results)} "
            f"matching item"
            f"{'s' if len(results) != 1 else ''}."
        ),
        items=results,
        query={
            "q": command.name or payload.transcript,
            "max_price": command.max_price,
            "brand": command.brand,
        },
    )