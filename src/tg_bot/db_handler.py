"""Database access helpers for the Telegram bot.

This module owns the async SQLAlchemy session lifecycle used by the bot and
provides small query/update helpers for the most common user, category, and
item operations.
"""

import asyncio
from typing import List
from aiogram import types
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import delete, and_
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from contextlib import asynccontextmanager
from typing import Optional
from src.db_client.models import *
from src.logger import logger
from src.settings import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME


def build_db_config() -> str:
    """Build the async PostgreSQL connection URL from settings."""
    return f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class SessionManager:
    """Create and cache SQLAlchemy engines plus the async session factory."""

    def __init__(self, db_config: str):
        self.async_engine = create_async_engine(db_config)
        self.sync_engine = create_sync_engine(db_config.replace("postgresql+asyncpg", "postgresql"))
        self.async_session = None

    async def init_async_session(self):
        """Initialize the async session factory once for the process."""
        if self.async_session is not None:
            raise RuntimeError("Async session already initialized")
        self.async_session = sessionmaker(self.async_engine, expire_on_commit=False, class_=AsyncSession)
        logger.info('Async session initialized')

    async def close_async_session(self):
        """Dispose of the async session factory reference."""
        if self.async_session is not None:
            await self.async_session.close()
            logger.info('Async session closed')
        self.async_session = None

    def get_sync_session(self):
        """Create a plain synchronous SQLAlchemy session."""
        return sessionmaker(self.sync_engine)()

session_manager = None


def get_session_manager() -> SessionManager:
    """Return the process-wide session manager, creating it lazily."""
    global session_manager
    if session_manager is None:
        session_manager = SessionManager(build_db_config())
    return session_manager


async def init_engine():
    """Initialize async sessions and create tables if they do not exist yet."""
    manager = get_session_manager()
    await manager.init_async_session()
    Base.metadata.create_all(manager.sync_engine, checkfirst=True)
    logger.info('Database schema initialized')


@asynccontextmanager
async def get_session() -> AsyncSession:
    """Yield an async session with automatic commit/rollback handling."""
    manager = get_session_manager()
    if manager.async_session is None:
        await manager.init_async_session()

    async with manager.async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e


async def create_user(user: types.User) -> None:
    """Persist a Telegram user as an active bot user."""
    async with get_session() as session:
        try:
            user = TelegramBotUser(id=user.id, username=user.username, first_name=user.first_name, active=True)
            session.add(user)
        except Exception as e:
            logger.error(e)
            raise


async def is_active(user: types.User) -> bool:
    """Return whether the given Telegram user exists and is active."""
    async with get_session() as session:
        stmt = select(TelegramBotUser).where(TelegramBotUser.id == user.id)
        result = await session.execute(stmt)
        user = result.scalars().first()
        return user is not None and user.active


async def get_all_active_users():
    """Return the Telegram ids of all active users."""
    async with get_session() as session:
        stmt = select(TelegramBotUser).where(TelegramBotUser.active)
        result = await session.execute(stmt)
        return [user.id for user in result.scalars().all()]


async def is_admin_async(user_id: int) -> bool:
    """Return whether the given Telegram user id belongs to an admin."""
    async with get_session() as session:
        stmt = select(AdminUser).where(AdminUser.user_id == user_id)
        result = await session.execute(stmt)
        admin_user = result.scalars().first()
        return admin_user is not None and admin_user.is_admin


async def activate_user_by_id_async(user_id: int) -> None:
    """Mark a user as active if the user exists."""
    async with get_session() as session:
        stmt = select(TelegramBotUser).where(TelegramBotUser.id == user_id)
        result = await session.execute(stmt)
        user = result.scalars().first()
        if user:
            user.active = True
            await session.commit()


async def deactivate_user_by_id_async(user_id: int) -> None:
    """Mark a user as inactive if the user exists."""
    async with get_session() as session:
        stmt = select(TelegramBotUser).where(TelegramBotUser.id == user_id)
        result = await session.execute(stmt)
        user = result.scalars().first()
        if user:
            user.active = False
            await session.commit()


async def get_user_by_username_async(username: str) -> Optional[TelegramBotUser]:
    """Fetch a Telegram bot user by Telegram username."""
    async with get_session() as session:
        stmt = select(TelegramBotUser).where(TelegramBotUser.username == username)
        result = await session.execute(stmt)
        user = result.scalars().first()
        return user


async def get_user_by_id_async(user_id: int) -> Optional[TelegramBotUser]:
    """Fetch a Telegram bot user by Telegram id."""
    async with get_session() as session:
        stmt = select(TelegramBotUser).where(TelegramBotUser.id == user_id)
        result = await session.execute(stmt)
        user = result.scalars().first()
        return user


async def get_admin_users_ids() -> List[int]:
    """Return all Telegram ids that currently have admin access."""
    async with get_session() as session:
        stmt = select(AdminUser).where(AdminUser.is_admin == True)
        result = await session.execute(stmt)
        return [admin_user.user_id for admin_user in result.scalars().all()]


async def get_unpublished_items(user_id: int) -> List[VintedItem]:
    """Return unseen items for all categories subscribed to by a user."""
    async with get_session() as session:
        stmt = (
            select(VintedItem)
            .join(UserCategory, VintedItem.category_id == UserCategory.category_id)
            .where(
                and_(
                    UserCategory.user_id == user_id,
                    VintedItem.unique_id.notin_(
                        select(UserPublishedItem.item_id).where(UserPublishedItem.user_id == user_id)
                    )
                )
            )
            .order_by(VintedItem.brand_name, VintedItem.price)
        )
        result = await session.execute(stmt)
        items = result.scalars().all()
        return items


async def add_published_item(user_id: int, item_id: int) -> None:
    """Record that an item has already been shown to a specific user."""
    async with get_session() as session:
        user_published_item = UserPublishedItem(user_id=user_id, item_id=item_id)
        session.add(user_published_item)


async def get_categories() -> List[Category]:
    """Return all saved categories available in the system."""
    async with get_session() as session:
        stmt = select(Category)
        result = await session.execute(stmt)
        categories = result.scalars().all()
        return categories


async def get_user_categories(user_id: int) -> List[Category]:
    """Return all categories currently assigned to a user."""
    async with get_session() as session:
        stmt = select(Category).join(UserCategory).where(UserCategory.user_id == user_id)
        result = await session.execute(stmt)
        user_categories = result.scalars().all()
        return user_categories


async def clear_table() -> None:
    """Remove all published-item and parsed-item rows.

    Categories and users are left intact.
    """
    async with get_session() as session:
        await session.execute(delete(UserPublishedItem))
        await session.execute(delete(VintedItem))
        await session.commit()


async def add_category_to_user(user_id: int, category_id: int):
    """Attach a category to a user if that link does not already exist."""
    async with get_session() as session:
        # Check if the user already has the category
        stmt = select(UserCategory).where(
            (UserCategory.user_id == user_id) & (UserCategory.category_id == category_id)
        )
        result = await session.execute(stmt)
        user_category = result.scalars().first()

        if user_category is None:
            # Create a new UserCategory record if it doesn't exist
            user_category = UserCategory(user_id=user_id, category_id=category_id)
            session.add(user_category)
            await session.commit()


async def create_category(category_name: str) -> Category:
    """Create and return a new category row."""
    async with get_session() as session:
        category = Category(name=category_name)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        return category


async def get_unpublished_items_by_category(user_id: int, category_id: int) -> List[VintedItem]:
    """Return unseen items for one user within one category."""
    async with get_session() as session:
        stmt = stmt = (
            select(VintedItem)
            .where(VintedItem.category_id == category_id)
            .where(VintedItem.unique_id.notin_(
                select(UserPublishedItem.item_id).where(UserPublishedItem.user_id == user_id)
            ))
            .order_by(VintedItem.brand_name, VintedItem.price)
        )
        result = await session.execute(stmt)
        unpublished_items = result.scalars().all()
        return unpublished_items


async def delete_user_category(user_id: int, category_id: int):
    """Delete the link between a user and a category."""
    async with get_session() as session:
        stmt = (
            delete(UserCategory)
            .where(
                (UserCategory.user_id == user_id) & (UserCategory.category_id == category_id)
            )
        )
        await session.execute(stmt)
        await session.commit()


async def get_users_for_category(category_id: int) -> List[TelegramBotUser]:
    """Return every user currently linked to the given category."""
    async with get_session() as session:
        stmt = (
            select(TelegramBotUser)
            .join(UserCategory, UserCategory.user_id == TelegramBotUser.id)
            .where(UserCategory.category_id == category_id)
        )
        result = await session.execute(stmt)
        users = result.scalars().all()
        return users


async def delete_category(category_id: int):
    """Delete a category row by its primary key."""
    async with get_session() as session:
        stmt = delete(Category).where(Category.id == category_id)
        await session.execute(stmt)
        await session.commit()
