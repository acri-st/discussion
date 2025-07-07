"""Contains:
- Event message send to MQ
"""

from datetime import datetime, timezone

from msfwk.context import current_transaction
from msfwk.desp.rabbitmq.mq_callback import InternalHTTPCallback
from msfwk.desp.rabbitmq.mq_message import (
    AutoModerationType,
    DespFonctionnalArea,
    DespMQMessage,
    ModerationEventStatus,
    MQAutoModerationModel,
    MQContentByTypeModel,
    MQContentModel,
    MQContentType,
)
from msfwk.exceptions import MQClientSendDataFailedError
from msfwk.models import DespUser
from msfwk.mqclient import RabbitMQConfig, send_mq_message
from msfwk.utils.logging import get_logger

from discussion.models.constants import CONTENT_BLOCKED
from discussion.models.exceptions import SendPostModerationError
from discussion.models.interfaces import DiscussionPostResponse, EditPostBody

logger = get_logger(__name__)


class ValidatePostMessage(DespMQMessage):
    """validate a Post"""

    def __init__(self, post: DiscussionPostResponse, text: str, user: DespUser) -> "ValidatePostMessage":
        body = {
            "status": ModerationEventStatus.Auto_Pending,
            "content_id": str(post.id),
            "user_id": user.id,
            "date": datetime.now(timezone.utc),
            "url": "",
            "fonctionnal_area": DespFonctionnalArea.DiscussionPost,
            "content": get_post_mq_content(text),
            "auto_mod_routing": [MQAutoModerationModel(moderation_type=AutoModerationType.Text_Toxicity)],
            "reject_callbacks": [
                InternalHTTPCallback(
                    service="discussion",
                    method="PUT",
                    url=f"/post/moderate/{post.id}",
                    headers={"Content-Type": "application/json"},
                    payload=EditPostBody(text=CONTENT_BLOCKED).model_dump(),
                )
            ],
            "accept_callbacks": [],
            "history": [],
            "transaction_id": current_transaction.get(),
        }
        super().__init__(
            body, exchange=RabbitMQConfig.MODERATION_EXCHANGE, routing_key=RabbitMQConfig.TO_AUTO_TEXT_TOXICITY_RKEY
        )

    def get_id(self, body: dict) -> str:
        """Override the get_id"""
        return f"{body['fonctionnal_area'].value}-{body.get('content_id', super().get_id(body))}"


def get_post_mq_content(text: str) -> list[MQContentByTypeModel]:
    """_summary_

    Args:
        text (str): text

    Returns:
        dict[str, str]: content
    """
    text_content = [MQContentModel(name="post_content", value=text)]
    return MQContentByTypeModel(data_by_type={MQContentType.Text: text_content})


async def send_post_to_moderation(post: DiscussionPostResponse, text: str, user: DespUser) -> None:
    """Send a validation event to the moderation queue

    Args:
        post (DiscussionPostResponse): _description_
        user (DespUser): _description_
        text (str): text of the topic

    Raises:
        SendModerationEventError: _description_
    """
    try:
        mq_message = ValidatePostMessage(post, text, user)
        await send_mq_message(mq_message)
        logger.info("Moderation event send for Message %s", text)
    except MQClientSendDataFailedError as mqe:
        message = f"Failed to send data to MQ {mq_message.as_payload()}"
        logger.exception(message, exc_info=mqe)
        raise SendPostModerationError from mqe


class ValidateTopicMessage(DespMQMessage):
    """Validate a Topic"""

    def __init__(self, topic_id: int, topic_title: str, user: DespUser) -> "ValidatePostMessage":
        body = {
            "status": ModerationEventStatus.Auto_Pending,
            "content_id": str(topic_id),
            "user_id": user.id,
            "date": datetime.now(timezone.utc),
            "url": "",
            "fonctionnal_area": DespFonctionnalArea.DiscussionTopic,
            "content": get_validate_topic_mq_content(topic_title),
            "auto_mod_routing": [MQAutoModerationModel(moderation_type=AutoModerationType.Text_Toxicity)],
            "reject_callbacks": [
                InternalHTTPCallback(
                    service="discussion",
                    method="DELETE",
                    url=f"/topic/moderate/{topic_id}",
                    headers={"Content-Type": "application/json"},
                    payload=EditPostBody(text=CONTENT_BLOCKED).model_dump(),
                )
            ],
            "accept_callbacks": [],
            "history": [],
            "transaction_id": current_transaction.get(),
        }
        super().__init__(
            body, exchange=RabbitMQConfig.MODERATION_EXCHANGE, routing_key=RabbitMQConfig.TO_AUTO_TEXT_TOXICITY_RKEY
        )

    def get_id(self, body: dict) -> str:
        """Override the get_id"""
        return f"{body['fonctionnal_area'].value}-{body.get('content_id', super().get_id(body))}"


def get_validate_topic_mq_content(topic_title: str) -> list[MQContentByTypeModel]:
    """Get the content for the validate_topic

    Args:
        topic_title (str):; text
        post_text (str): text

    Returns:
        dict[str, str]: content
    """
    text_content = [MQContentModel(name="topic_title", value=topic_title)]
    return MQContentByTypeModel(data_by_type={MQContentType.Text: text_content})


async def send_topic_to_moderation(topic_id: int, topic_title: str, user: DespUser) -> None:
    """Send a validation event to the moderation queue

    Args:
        topic_id (int): _description_
        user (DespUser): _description_
        topic_title (str): text of the topic

    Raises:
        SendModerationEventError: _description_
    """
    try:
        mq_message = ValidateTopicMessage(topic_id, topic_title, user)
        await send_mq_message(mq_message)
        logger.info("Moderation event send for Topic %s", topic_title)
    except MQClientSendDataFailedError as mqe:
        message = f"Failed to send data to MQ {mq_message.as_payload()}"
        logger.exception(message, exc_info=mqe)
        raise SendPostModerationError from mqe
