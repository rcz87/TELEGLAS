import sqlite3
import asyncio
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from loguru import logger
from config.settings import settings
import aiosqlite
import json


@dataclass
class UserSubscription:
    """User subscription data model"""

    user_id: int
    symbol: str
    alert_types: List[str]  # ['liquidation', 'whale', 'funding']
    threshold_usd: Optional[float] = None
    is_active: bool = True
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            import datetime

            self.created_at = datetime.datetime.utcnow().isoformat()


class DatabaseManager:
    """SQLite database manager for user subscriptions and preferences"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DATABASE_URL.replace("sqlite:///", "")
        self._connection_pool = None

    async def initialize(self):
        """Initialize database and create tables"""
        await self._create_tables()
        logger.info(f"Database initialized at {self.db_path}")

    async def _create_tables(self):
        """Create necessary database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # User subscriptions table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    alert_types TEXT NOT NULL,  -- JSON array
                    threshold_usd REAL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, symbol)
                )
            """
            )

            # Whale transactions cache table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS whale_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_hash TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    amount_usd REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Liquidation events cache table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS liquidation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    liquidation_usd REAL NOT NULL,
                    side TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # System alerts table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS system_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,  -- JSON
                    is_sent BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for better performance
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_subscriptions_symbol ON user_subscriptions(symbol)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_whale_transactions_timestamp ON whale_transactions(timestamp)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_liquidation_events_timestamp ON liquidation_events(timestamp)"
            )

            await db.commit()

    async def add_user_subscription(self, subscription: UserSubscription) -> bool:
        """Add or update user subscription"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                alert_types_json = json.dumps(subscription.alert_types)

                await db.execute(
                    """
                    INSERT OR REPLACE INTO user_subscriptions 
                    (user_id, symbol, alert_types, threshold_usd, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        subscription.user_id,
                        subscription.symbol,
                        alert_types_json,
                        subscription.threshold_usd,
                        subscription.is_active,
                    ),
                )

                await db.commit()
                logger.info(
                    f"Added/updated subscription for user {subscription.user_id}, symbol {subscription.symbol}"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to add user subscription: {e}")
            return False

    async def get_user_subscriptions(self, user_id: int) -> List[UserSubscription]:
        """Get all subscriptions for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT user_id, symbol, alert_types, threshold_usd, is_active, created_at
                    FROM user_subscriptions
                    WHERE user_id = ? AND is_active = 1
                """,
                    (user_id,),
                )

                rows = await cursor.fetchall()
                subscriptions = []

                for row in rows:
                    subscription = UserSubscription(
                        user_id=row[0],
                        symbol=row[1],
                        alert_types=json.loads(row[2]),
                        threshold_usd=row[3],
                        is_active=bool(row[4]),
                        created_at=row[5],
                    )
                    subscriptions.append(subscription)

                return subscriptions

        except Exception as e:
            logger.error(f"Failed to get user subscriptions: {e}")
            return []

    async def get_subscribers_for_symbol(
        self, symbol: str, alert_type: str
    ) -> List[UserSubscription]:
        """Get all users subscribed to a symbol for specific alert type"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT user_id, symbol, alert_types, threshold_usd, is_active, created_at
                    FROM user_subscriptions
                    WHERE symbol = ? AND is_active = 1
                """,
                    (symbol,),
                )

                rows = await cursor.fetchall()
                subscriptions = []

                for row in rows:
                    alert_types = json.loads(row[2])
                    if alert_type in alert_types:
                        subscription = UserSubscription(
                            user_id=row[0],
                            symbol=row[1],
                            alert_types=alert_types,
                            threshold_usd=row[3],
                            is_active=bool(row[4]),
                            created_at=row[5],
                        )
                        subscriptions.append(subscription)

                return subscriptions

        except Exception as e:
            logger.error(f"Failed to get subscribers for symbol {symbol}: {e}")
            return []

    async def remove_user_subscription(self, user_id: int, symbol: str) -> bool:
        """Remove user subscription"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE user_subscriptions 
                    SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND symbol = ?
                """,
                    (user_id, symbol),
                )

                await db.commit()
                logger.info(f"Removed subscription for user {user_id}, symbol {symbol}")
                return True

        except Exception as e:
            logger.error(f"Failed to remove user subscription: {e}")
            return False

    async def cache_whale_transaction(
        self, tx_hash: str, symbol: str, side: str, amount_usd: float, timestamp: str
    ):
        """Cache whale transaction to avoid duplicates"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO whale_transactions 
                    (transaction_hash, symbol, side, amount_usd, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (tx_hash, symbol, side, amount_usd, timestamp),
                )

                await db.commit()

        except Exception as e:
            logger.error(f"Failed to cache whale transaction: {e}")

    async def is_whale_transaction_cached(self, tx_hash: str) -> bool:
        """Check if whale transaction is already cached"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT 1 FROM whale_transactions WHERE transaction_hash = ?
                """,
                    (tx_hash,),
                )

                result = await cursor.fetchone()
                return result is not None

        except Exception as e:
            logger.error(f"Failed to check whale transaction cache: {e}")
            return False

    async def add_system_alert(
        self, alert_type: str, message: str, data: Dict[str, Any] = None
    ):
        """Add system alert for broadcasting"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                data_json = json.dumps(data) if data else None

                await db.execute(
                    """
                    INSERT INTO system_alerts (alert_type, message, data)
                    VALUES (?, ?, ?)
                """,
                    (alert_type, message, data_json),
                )

                await db.commit()

        except Exception as e:
            logger.error(f"Failed to add system alert: {e}")

    async def get_pending_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending system alerts"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT id, alert_type, message, data, created_at
                    FROM system_alerts
                    WHERE is_sent = 0
                    ORDER BY created_at ASC
                    LIMIT ?
                """,
                    (limit,),
                )

                rows = await cursor.fetchall()
                alerts = []

                for row in rows:
                    alert = {
                        "id": row[0],
                        "alert_type": row[1],
                        "message": row[2],
                        "data": json.loads(row[3]) if row[3] else None,
                        "created_at": row[4],
                    }
                    alerts.append(alert)

                return alerts

        except Exception as e:
            logger.error(f"Failed to get pending alerts: {e}")
            return []

    async def mark_alert_sent(self, alert_id: int):
        """Mark system alert as sent"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE system_alerts SET is_sent = 1 WHERE id = ?
                """,
                    (alert_id,),
                )

                await db.commit()

        except Exception as e:
            logger.error(f"Failed to mark alert as sent: {e}")

    async def cleanup_old_data(self, days: int = 7):
        """Clean up old cached data"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cutoff_date = f"-{days} days"

                await db.execute(
                    """
                    DELETE FROM whale_transactions WHERE created_at < datetime('now', ?)
                """,
                    (cutoff_date,),
                )

                await db.execute(
                    """
                    DELETE FROM liquidation_events WHERE created_at < datetime('now', ?)
                """,
                    (cutoff_date,),
                )

                await db.execute(
                    """
                    DELETE FROM system_alerts WHERE created_at < datetime('now', ?) AND is_sent = 1
                """,
                    (cutoff_date,),
                )

                await db.commit()
                logger.info(f"Cleaned up data older than {days} days")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")


# Global database instance
db_manager = DatabaseManager()
