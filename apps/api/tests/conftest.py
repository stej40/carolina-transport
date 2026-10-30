from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app
from app.models import User
from app.security import hash_password


@pytest.fixture
async def session_maker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override() -> AsyncIterator[AsyncSession]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = override
    app.state.session_maker = maker
    yield maker
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def client(session_maker: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def add_user(session_maker: async_sessionmaker[AsyncSession]) -> Callable[..., Awaitable[User]]:
    async def _add(
        email: str,
        password: str = "secret123",
        roles: list[str] | None = None,
        name: str = "Test User",
    ) -> User:
        user = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
            roles=roles or ["driver"],
        )
        async with session_maker() as session:
            session.add(user)
            await session.commit()
        return user

    return _add


async def login(client: AsyncClient, email: str, password: str = "secret123") -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    body: dict[str, str] = response.json()
    return body


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def idem() -> dict[str, str]:
    """Fresh Idempotency-Key headers - one per intended write (constraint 4)."""
    return {"Idempotency-Key": str(uuid4())}
