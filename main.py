import asyncio
import signal
import sys
from typing import List
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config.settings import settings
from core.database import db_manager
from handlers.telegram_bot import telegram_bot
from services.liquidation_monitor import liquidation_monitor
from services.whale_watcher import whale_watcher
from services.funding_rate_radar import funding_rate_radar
from utils.process_lock import ProcessLock, check_existing_instances


class CryptoSatBot:
    """Main CryptoSat bot application orchestrator"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running = False
        self.monitoring_tasks: List[asyncio.Task] = []

    async def initialize(self):
        """Initialize all components"""
        logger.info("[INIT] Initializing CryptoSat Bot...")

        # Validate settings
        settings.validate()
        logger.info("[OK] Configuration validated")

        # Initialize database
        await db_manager.initialize()
        logger.info("[OK] Database initialized")

        # Initialize Telegram bot
        await telegram_bot.initialize()
        logger.info("[OK] Telegram bot initialized")

        # Set up scheduler for periodic tasks
        self._setup_scheduler()
        logger.info("[OK] Scheduler configured")

        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()

        logger.info("[DONE] CryptoSat Bot initialization complete!")

    def _setup_scheduler(self):
        """Set up periodic tasks with APScheduler"""
        # Cleanup old data daily at 2 AM UTC
        self.scheduler.add_job(
            self._cleanup_data,
            "cron",
            hour=2,
            minute=0,
            id="cleanup_data",
            name="Cleanup old data",
        )

        # Health check every 5 minutes
        self.scheduler.add_job(
            self._health_check,
            "interval",
            minutes=5,
            id="health_check",
            name="Health check",
        )

        # Alert broadcasting task every 30 seconds
        self.scheduler.add_job(
            self._broadcast_pending_alerts,
            "interval",
            seconds=30,
            id="broadcast_alerts",
            name="Broadcast pending alerts",
        )

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def start_monitoring_services(self):
        """Start background monitoring services based on configuration"""
        logger.info("[START] Starting monitoring services...")

        # ONLY start whale watching if enabled
        if settings.ENABLE_WHALE_ALERTS:
            logger.info("[START] Starting whale monitoring (ENABLE_WHALE_ALERTS=true)")
            task = asyncio.create_task(whale_watcher.start_monitoring())
            self.monitoring_tasks.append(task)
        else:
            logger.info("[SKIP] Whale monitoring disabled (ENABLE_WHALE_ALERTS=false)")

        # All other monitors (liquidation, funding) are MANUAL ONLY - do not start automatically
        logger.info("[INFO] Liquidation and funding rate monitoring are MANUAL ONLY")
        logger.info("[INFO] Use Telegram commands to trigger manual scans")

        logger.info("[OK] Monitoring services configuration complete")

    async def _cleanup_data(self):
        """Clean up old data from database"""
        try:
            logger.info("[CLEANUP] Starting data cleanup...")
            await db_manager.cleanup_old_data(days=7)
            logger.info("[OK] Data cleanup completed")
        except Exception as e:
            logger.error(f"[ERROR] Data cleanup failed: {e}")

    async def _health_check(self):
        """Perform health check on all services"""
        try:
            # Check monitoring tasks
            for i, task in enumerate(self.monitoring_tasks):
                if task.done():
                    logger.warning(
                        f"[WARN] Monitoring task {i} has stopped: {task.exception()}"
                    )
                    # Restart the task if it failed
                    self.monitoring_tasks.pop(i)
                    await self._restart_monitoring_task(i)

            # Log basic health status
            logger.info("[HEALTH] Health check passed - all systems operational")

        except Exception as e:
            logger.error(f"[ERROR] Health check failed: {e}")

    async def _restart_monitoring_task(self, task_index: int):
        """Restart a failed monitoring task"""
        try:
            if task_index == 0:  # Liquidation monitor
                task = asyncio.create_task(liquidation_monitor.start_monitoring())
                self.monitoring_tasks.insert(0, task)
                logger.info("[RESTART] Restarted liquidation monitoring")
            elif task_index == 1:  # Whale watcher
                task = asyncio.create_task(whale_watcher.start_monitoring())
                self.monitoring_tasks.insert(1, task)
                logger.info("[RESTART] Restarted whale monitoring")
            elif task_index == 2:  # Funding rate radar
                task = asyncio.create_task(funding_rate_radar.start_monitoring())
                self.monitoring_tasks.insert(2, task)
                logger.info("[RESTART] Restarted funding rate monitoring")
            elif task_index >= 3:  # Telegram bot (could be at any position after monitors)
                task = asyncio.create_task(telegram_bot.start())
                self.monitoring_tasks.insert(task_index, task)
                logger.info("[RESTART] Restarted Telegram bot")
        except Exception as e:
            logger.error(f"[ERROR] Failed to restart monitoring task {task_index}: {e}")

    async def _broadcast_pending_alerts(self):
        """Broadcast pending alerts to Telegram channel based on configuration"""
        try:
            # Check if broadcasting is enabled
            if not settings.ENABLE_BROADCAST_ALERTS and not settings.ENABLE_WHALE_ALERTS:
                return  # No broadcasting allowed

            alerts = await db_manager.get_pending_alerts(limit=10)
            
            # Handle case where alerts is empty due to cancellation
            if not alerts:
                return

            for alert in alerts:
                try:
                    # Only broadcast whale alerts if general broadcasting is disabled but whale alerts are enabled
                    if not settings.ENABLE_BROADCAST_ALERTS and settings.ENABLE_WHALE_ALERTS:
                        if alert.get("alert_type") != "whale":
                            continue  # Skip non-whale alerts
                    
                    await telegram_bot.broadcast_alert(alert["message"])
                    await db_manager.mark_alert_sent(alert["id"])
                    logger.debug(f"Broadcasted alert {alert['id']} (type: {alert.get('alert_type', 'unknown')})")
                except asyncio.CancelledError:
                    logger.warning("Alert broadcasting cancelled")
                    break
                except Exception as alert_error:
                    logger.error(f"Failed to broadcast alert {alert.get('id', 'unknown')}: {alert_error}")
                    continue

            if alerts:
                logger.info(f"[BROADCAST] Broadcasted {len(alerts)} alerts")

        except asyncio.CancelledError:
            logger.warning("Broadcast pending alerts task cancelled")
        except Exception as e:
            logger.error(f"[ERROR] Failed to broadcast alerts: {e}")

    async def start(self):
        """Start the CryptoSat bot"""
        try:
            # Initialize all components
            await self.initialize()

            # Start monitoring services
            await self.start_monitoring_services()

            # Start scheduler
            self.scheduler.start()
            logger.info("[SCHEDULER] Scheduler started")

            # Start Telegram bot in background (non-blocking)
            # Use create_task with proper error handling
            try:
                telegram_task = asyncio.create_task(telegram_bot.start())
                self.monitoring_tasks.append(telegram_task)
                logger.info("[OK] Telegram bot task created successfully")
            except Exception as e:
                logger.error(f"[ERROR] Failed to create Telegram bot task: {e}")
                raise

            # Set running state
            self.running = True
            logger.info("[OPERATIONAL] CryptoSat Bot is now fully operational!")

            # Keep the main coroutine running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"[ERROR] Failed to start CryptoSat Bot: {e}")
            await self.shutdown()
            sys.exit(1)

    async def shutdown(self):
        """Graceful shutdown of all components"""
        if not self.running:
            return

        logger.info("[SHUTDOWN] Initiating graceful shutdown...")
        self.running = False

        try:
            # Stop monitoring tasks gracefully
            # First stop whale watcher to properly close session
            try:
                await whale_watcher.stop_monitoring()
            except Exception as e:
                logger.warning(f"[WARNING] Error stopping whale watcher: {e}")

            # Cancel other monitoring tasks
            for i, task in enumerate(self.monitoring_tasks):
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info(f"[STOPPED] Stopped monitoring task {i}")

            self.monitoring_tasks.clear()

            # Stop scheduler
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("[STOPPED] Scheduler stopped")

            # Stop Telegram bot
            await telegram_bot.stop()
            logger.info("[STOPPED] Telegram bot stopped")

            logger.info("[COMPLETE] CryptoSat Bot shutdown complete")

        except Exception as e:
            logger.error(f"[ERROR] Error during shutdown: {e}")


async def main():
    """Main entry point"""
    # Check for existing instances before starting
    if check_existing_instances():
        logger.error("[EXIT] Another bot instance is already running. Exiting.")
        sys.exit(1)
    
    # Use process lock to ensure only one instance runs
    with ProcessLock():
        # Debug the LOG_LEVEL value
        print(f"DEBUG: LOG_LEVEL value = '{settings.LOG_LEVEL}'")
        print(f"DEBUG: LOG_LEVEL type = {type(settings.LOG_LEVEL)}")
        print(f"DEBUG: LOG_LEVEL.lower() = '{settings.LOG_LEVEL.lower()}'")
        
        # Configure logging
        logger.remove()  # Remove default handler
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO",  # Hardcode for now to fix the issue
        )

        # Add file logging if specified
        if settings.LOG_FILE:
            # Ensure logs directory exists
            import os
            log_dir = os.path.dirname(settings.LOG_FILE)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                logger.info(f"Created logs directory: {log_dir}")
            
            logger.add(
                settings.LOG_FILE,
                rotation="10 MB",
                retention="7 days",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level="INFO",
            )

        logger.info(
            "[STARTUP] CryptoSat Bot - High-Frequency Trading Signals & Market Intelligence"
        )
        logger.info("[STARTUP] Powered by CoinGlass API v4")

        # Create and start the bot
        bot = CryptoSatBot()

        try:
            await bot.start()
        except KeyboardInterrupt:
            logger.info("[INTERRUPT] Received keyboard interrupt")
        except Exception as e:
            logger.error(f"[FATAL] Fatal error: {e}")
        finally:
            await bot.shutdown()


if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())
