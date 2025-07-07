from typing import AsyncGenerator
from unittest.mock import  MagicMock, Mock, patch
import pytest
from sqlalchemy import Column, MetaData, Table
from msfwk.schema.schema import Schema
from msfwk.utils.logging import ACRILoggerAdapter, get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger: ACRILoggerAdapter = get_logger("test.utils")

@pytest.fixture(autouse=True)
async def mock_database_class() -> AsyncGenerator[Schema, None] :
    """Mock the database and return the session result can be mocked
    record = MagicMock(MappingResult)
    record._mapping = {"field1":1}
    mock_database_class.execute.return_value=[record]
    """
    logger.info("Mocking the database session")
    with patch("msfwk.database.get_schema") as mock:
        schema = Schema("postgresql+asyncpg://test:test@test:5432/test")
        session = MagicMock(spec=AsyncSession)
        session.__aenter__.return_value = session
        schema.get_async_session = Mock(return_value=session)
        mock.return_value = schema
        yield schema
    logger.info("Mocking database reset")
    
test_storage_config={
    "rabbitmq":{
        "mq_server": "Test_conf_mq_server", 
        "mq_port": 5672,
        "user": "test",
        "password": "psw_test"
    },
    "services": {
        "moderation": {
            "manual_moderation_queue_name": "test",
            "error_moderation_queue_name": "test",
            "moderation_exchange": "test",
            "to_manual_routing_key": "test",
            "to_error_routing_key": "test",
        },
        "moderation_handling": {
            "handling_moderation_queue_name": "test",
            "to_handling_routing_key": "test",
        },
        "automoderation":{
            "text_toxicity_automoderation_queue_name": "test",
            "to_auto_text_toxicity_routing_key": "test"
        },
        "discussion":{
            "discourse_host": "https://discourse.collaborative-services.acri-st.fr",
            "api_key": "fa0c184dcf2b834819309db5d644cf6de0b977f59808638a9040c5616bef54f1"
        }
    }
}

def fake_table(name:str,columns:list[str])-> Table:
    return Table(name,MetaData(),*[Column(col) for col in columns])