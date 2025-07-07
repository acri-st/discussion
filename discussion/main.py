"""Main module for the discussion service"""

from msfwk.application import app
from msfwk.context import register_init
from msfwk.mqclient import load_default_rabbitmq_config
from msfwk.utils.logging import get_logger

from .routes.discourse import router as discourse_router

logger = get_logger("application")


async def init(config: dict) -> bool:
    """Initialize the application"""
    return load_default_rabbitmq_config(config)


# Application Lifecycle
register_init(init)

app.include_router(discourse_router)
