from unittest.mock import AsyncMock, MagicMock, Mock, patch
from msfwk.models import DespUser
from msfwk.utils.user import set_current_user
import pytest
import aiohttp
from fastapi.testclient import TestClient
from msfwk.utils.conftest import load_json, mock_read_config,mock_http_client  # noqa: F401
from msfwk.utils.logging import ACRILoggerAdapter, get_logger
from .utils import fake_table, mock_database_class, test_storage_config
logger: ACRILoggerAdapter = get_logger("test")


def handle_discussion_requests(path: str,
        query_data=None,
        post_data=None,
        raw: bool = False,
        streamed: bool = False,
        files=None,
        timeout=None,
        obey_rate_limit: bool = True,
        retry_transient_errors = None,
        max_retries: int = 10,
        **kwargs):
    logger.debug("=====>Catching %s %s",path,query_data or post_data)
    if path == '/c/38/show.json':
        mocked_response = MagicMock(spec=aiohttp.ClientResponse)
        mocked_response.status_code = 200
        mocked_response.json = AsyncMock(return_value=load_json(__file__, 'get_category.json'))
        mocked_response.__aenter__.return_value = mocked_response
        return mocked_response
    if path == "/c//38.json":
        mocked_response = MagicMock(spec=aiohttp.ClientResponse)
        mocked_response.status = 200
        mocked_response.json = AsyncMock(return_value=load_json(__file__, 'get_topics.json'))
        mocked_response.__aenter__.return_value = mocked_response
        return mocked_response
    if path == '/c/1/show.json':
        mocked_response = MagicMock(spec=aiohttp.ClientResponse)
        mocked_response.status = 404
        mocked_response.__aenter__.return_value = mocked_response
        logger.debug(mocked_response)
        return mocked_response
    if path == '/categories.json':
        mocked_response = MagicMock(spec=aiohttp.ClientResponse)
        mocked_response.status = 200
        mocked_response.json = AsyncMock(return_value=load_json(__file__, 'get_category.json'))
        mocked_response.__aenter__.return_value = mocked_response
        return mocked_response
    if path == "/c/uncategorized/1.json":
        mocked_response = MagicMock(spec=aiohttp.ClientResponse)
        mocked_response.status = 200
        mocked_response.json = AsyncMock(return_value=load_json(__file__, 'get_topics.json'))
        mocked_response.__aenter__.return_value = mocked_response
        return mocked_response
    if path == "/users.json":
        mocked_response = MagicMock(spec=aiohttp.ClientResponse)
        mocked_response.status = 200
        mocked_response.json = AsyncMock(return_value=load_json(__file__, 'create_user.json'))
        mocked_response.__aenter__.return_value = mocked_response
        return mocked_response
    logger.debug("=====>Not Mocked %s %s",path,query_data or post_data)

@pytest.mark.component
def test_get_already_existing_discussion(mock_read_config,mock_database_class):  # noqa: F811
    mock_read_config.return_value = test_storage_config
    with patch("aiohttp.ClientSession") as mock:
        mock.return_value = mock # On new instance creation
        mock.__aenter__.return_value= mock # inside a with
        mock.get = MagicMock(side_effect=handle_discussion_requests)
        category_db = Mock()
        category_db.all.return_value=[(1,38,None)]
        mock_database_class.tables = {"Discourses":fake_table("Discourses",["id","assetId","categoryId","url"])}
        mock_database_class.get_async_session().execute = AsyncMock(return_value=category_db) 
        from discussion.main import app
        set_current_user(DespUser(username="utest",display_name="Unit test",user_id="utest"))
        with TestClient(app) as client:
            response = client.get("/discussion/00000000-00b0-00bb-b00b-00b000000000")
            assert response.status_code == 200
            assert response.json() ==  {    'data': {
        'id': 1,
        'name': 'Uncategorized',
        'topics': [
            {
                'category_id': 38,
                'created_at': '2024-10-28T09:42:38.860Z',
                'fancy_title': 'About the 1 category',
                'id': 66,
                'posts': [],
                'posts_count': 1,
                'slug': 'about-the-1-category',
                'title': 'About the 1 category',
            },
            {
                 'category_id': 38,
                 'created_at': '2024-10-28T09:56:31.565Z',
                 'fancy_title': 'Test_ds: An awesome new topic',
                 'id': 67,
                 'posts': [],
                 'posts_count': 1,
                 'slug': 'test-ds-an-awesome-new-topic',
                 'title': 'Test_ds: An awesome new topic',
                },
        ],
    },} 

@pytest.mark.component
def test_get_not_existing_discussion(mock_read_config,mock_database_class):  # noqa: F811
    mock_read_config.return_value = test_storage_config
    with patch("aiohttp.ClientSession") as mock:
        mock.return_value = mock # On new instance creation
        mock.__aenter__.return_value= mock # inside a with
        response_mocker = MagicMock(side_effect=handle_discussion_requests)
        mock.post = response_mocker 
        mock.get = response_mocker 
        category_db = Mock()
        category_db.all.return_value=[]
        mock_database_class.tables = {"Discourses":fake_table("Discourses",["id","assetId","categoryId","url"])}
        mock_database_class.get_async_session().execute = AsyncMock(return_value=category_db) 
        from discussion.main import app
        set_current_user(DespUser(username="utest",display_name="Unit test",user_id="utest"))
        with TestClient(app) as client:
            response = client.get("/discussion/00000000-00b0-00bb-b00b-00b000000000")
            assert response.status_code == 200
            assert response.json() ==  {    'data': {
        'id': 1,
        'name': 'Uncategorized',
        'topics': [
            {
                'category_id': 38,
                'created_at': '2024-10-28T09:42:38.860Z',
                'fancy_title': 'About the 1 category',
                'id': 66,
                'posts': [],
                'posts_count': 1,
                'slug': 'about-the-1-category',
                'title': 'About the 1 category',
            },
            {
                 'category_id': 38,
                 'created_at': '2024-10-28T09:56:31.565Z',
                 'fancy_title': 'Test_ds: An awesome new topic',
                 'id': 67,
                 'posts': [],
                 'posts_count': 1,
                 'slug': 'test-ds-an-awesome-new-topic',
                 'title': 'Test_ds: An awesome new topic',
                },
        ],
    },} 
