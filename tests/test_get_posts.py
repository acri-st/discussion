from unittest.mock import AsyncMock, MagicMock, Mock, patch
from msfwk.models import DespUser
from msfwk.utils.user import set_current_user
import pytest
import aiohttp
from fastapi.testclient import TestClient
from msfwk.utils.conftest import load_json, mock_read_config,mock_http_client  # noqa: F401
from msfwk.utils.logging import get_logger
from msfwk.context import current_config
from .utils import test_storage_config

logger = get_logger("test")

def handle_discourse_requests(path: str,
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
    if path == "/t/67.json":
        mock_get_category_response = MagicMock(spec=aiohttp.ClientResponse)
        mock_get_category_response.status = 200
        mock_get_category_response.json = AsyncMock(return_value=load_json(__file__, 'get_topic_posts.json'))
        mock_get_category_response.__aenter__.return_value = mock_get_category_response
        return mock_get_category_response
    if path == "/users.json":
        mocked_response = MagicMock(spec=aiohttp.ClientResponse)
        mocked_response.status = 200
        mocked_response.json = AsyncMock(return_value=load_json(__file__, 'create_user.json'))
        mocked_response.__aenter__.return_value = mocked_response
        return mocked_response


def test_get_posts( mock_read_config):  # noqa: F811
    mock_read_config.return_value = test_storage_config
    with patch("aiohttp.ClientSession") as mock:
        mock.return_value = mock # On new instance creation
        mock.__aenter__.return_value= mock # inside a with
        response_mocker = MagicMock(side_effect=handle_discourse_requests)
        response_mocker.__aenter__ = response_mocker
        mock.get = response_mocker 
        from discussion.main import app
        set_current_user(DespUser(username="utest",display_name="Unit test",user_id="utest"))
        with TestClient(app) as client:
            response = client.get("/topic/67")
            assert response.status_code == 200
            assert response.json() ==   {
        'data': {
            'category_id': 38,
            'created_at': '2024-10-28T09:56:31.565Z',
            'fancy_title': 'Test_ds: An awesome new topic',
            'id': 67,
            'posts': [
                {
                    'avatar_template': '/letter_avatar_proxy/v4/letter/t/ba8739/{size}.png',
                    'cooked': '<p>test_ds: An awesome new topic</p>',
                    'created_at': '2024-10-28T09:56:31.639Z',
                    'display_username': 'Testone Detest',
                    'id': 64,
                    'name': 'Testone Detest',
                    'topic_id': 67,
                    'user_id': 10,
                    'username': 'test1',
                },
            ],
            'posts_count': 1,
            'slug': 'test-ds-an-awesome-new-topic',
            'title': 'Test_ds: An awesome new topic',
        },
    } 

