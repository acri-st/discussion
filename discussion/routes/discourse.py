"""Discussion routes"""

from uuid import UUID

from fastapi import APIRouter
from msfwk.application import openapi_extra
from msfwk.models import BaseDespResponse, DespResponse, DespUser
from msfwk.notification import NotificationTemplate, send_email_to_mq
from msfwk.utils.logging import get_logger
from msfwk.utils.user import get_current_user

from discussion.models.constants import (
    CONTENT_TOO_SHORT,
    DEFAULT_INTERNAL_ERROR_MESSAGE,
    DISCOURSE_POST_CATEGORY_UUID,
    MISSING_CATEGORY_ERROR_MESSAGE,
    TITLE_TOO_SHORT,
)
from discussion.models.exceptions import (
    AuthenticationNeededError,
    DiscourseRequestError,
    DiscourseResourceUnavailableError,
    DiscourseUnavailableError,
)
from discussion.models.interfaces import (
    CreatePostBody,
    CreateTopicBody,
    DiscourseTopic,
    DiscussionPostResponse,
    DiscussionResponse,
    DiscussionTopicResponse,
    EditPostBody,
    TopicsReponse,
)
from discussion.routes.auth_service import get_current_user_roles, get_mail_from_desp_user_id
from discussion.services.asset import _get_asset_owner, get_asset
from discussion.services.discourse import (
    create_discourse_post,
    create_discourse_topic,
    delete_discourse_topic,
    edit_discourse_post,
    ensure_user,
    get_category_asset,
    get_discourse_category,
    get_discourse_post,
    get_discourse_posts,
    get_discourse_topic,
    get_discourse_topics,
)
from discussion.services.rabbitmq_events import send_post_to_moderation, send_topic_to_moderation

__all__ = ["router"]

router = APIRouter()
logger = get_logger("discussion")


@router.get(
    "/discussion/{asset_id}",
    response_model=BaseDespResponse[DiscussionResponse],
    summary=(
        "This method creates a discourse category associated with the given id "
        "if one has not been created, then it returns this categorie's topics"
    ),
    response_description="Returns discussion data",
    tags=["discussion"],
    openapi_extra=openapi_extra(secured=False, roles=["user"], internal=False),
)
async def get_category(asset_id: UUID) -> BaseDespResponse[DiscussionResponse]:
    """Get category data"""
    response = DiscussionResponse(id=0, name="", topics=[])
    try:
        # Everyone can see the discussions
        # Getting the id of the category associated to the asset
        asset_category_id = await get_category_asset(asset_id)
        # Retrieve the category of the asset
        category_response = await get_discourse_category(asset_category_id, asset_id)
        # Get all the topics associated to the category
        topics_response = await get_discourse_topics(category_response.slug, category_response.id)
        response = DiscussionResponse.from_reply(category_response, topics_response)
        return DespResponse(data=response)
    except (DiscourseUnavailableError, DiscourseResourceUnavailableError):
        return DespResponse(data=response, error=DEFAULT_INTERNAL_ERROR_MESSAGE)
    except DiscourseRequestError as dre:
        return DespResponse(data=response, error=str(dre))
    except AuthenticationNeededError as ane:
        return DespResponse(data=response, error=str(ane), http_status=401)


@router.get(
    "/topics/{slug}/{category}",
    response_model=BaseDespResponse[TopicsReponse],
    summary="This method returns all topics and latest posts in a specific category",
    response_description="Returns category topics",
    tags=["discussion"],
    openapi_extra=openapi_extra(secured=False, roles=["user"], internal=False),
)
async def get_topics(slug: str, category: int) -> BaseDespResponse[TopicsReponse]:
    """To get all topics (and other data) from a specific category"""
    response = {}
    try:
        # everyone can see the discussions
        topics: list[DiscourseTopic] = await get_discourse_topics(slug, category)
        query_result = TopicsReponse(topics=[DiscussionTopicResponse.from_reply(topic) for topic in topics])
        return DespResponse(data=query_result.model_dump(mode="json"))
    except DiscourseUnavailableError:
        return DespResponse(data=response, error=DEFAULT_INTERNAL_ERROR_MESSAGE, http_status=500)
    except DiscourseResourceUnavailableError:
        return DespResponse(data=response, error=MISSING_CATEGORY_ERROR_MESSAGE, http_status=404)
    except DiscourseRequestError as dre:
        return DespResponse(data=response, error=str(dre), http_status=500)
    except AuthenticationNeededError as ane:
        return DespResponse(data=response, error=str(ane), http_status=401)


@router.post(
    "/topic/{topic_id}",
    response_model=BaseDespResponse[DiscussionPostResponse],
    summary="This method creates a new post",
    response_description="Returns a new post",
    tags=["discussion"],
    openapi_extra=openapi_extra(secured=True, roles=["user"], internal=False),
)
async def create_post(topic_id: str, request_body: CreatePostBody) -> BaseDespResponse[DiscussionPostResponse]:
    """Use this method to create a new post in a topic"""
    user: DespUser = get_current_user()
    discourse_username = user.username
    response = {}
    try:
        await ensure_user(user)
        response = await create_discourse_post(
            discourse_username,
            topic_id,
            request_body.text,
        )
        query_result = DiscussionPostResponse(**response)
        await send_post_to_moderation(query_result, request_body.text, user)
        return DespResponse(data=query_result.model_dump(mode="json"))
    except (DiscourseUnavailableError, DiscourseResourceUnavailableError):
        return DespResponse(data=response, error=DEFAULT_INTERNAL_ERROR_MESSAGE)
    except DiscourseRequestError as dre:
        return DespResponse(data=response, error=str(dre))
    except AuthenticationNeededError as ane:
        return DespResponse(data=response, error=str(ane), http_status=401)


@router.put(
    "/post/{post_id}",
    response_model=BaseDespResponse[DiscussionPostResponse],
    summary="This method edits an existing post",
    response_description="Returns the updated post",
    tags=["discussion"],
    openapi_extra=openapi_extra(secured=True, roles=["moderator"], internal=True),
)
async def edit_post(post_id: str, request_body: EditPostBody) -> BaseDespResponse[DiscussionPostResponse]:
    """Use this method to edit an existing post"""
    response = {}
    try:
        response = await edit_discourse_post(
            post_id,
            request_body.text,
        )
        query_result = DiscussionPostResponse(**(response.model_dump()))
        return DespResponse(data=query_result.model_dump(mode="json"))
    except (DiscourseUnavailableError, DiscourseResourceUnavailableError):
        return DespResponse(data=response, error=DEFAULT_INTERNAL_ERROR_MESSAGE)
    except DiscourseRequestError as dre:
        return DespResponse(data=response, error=str(dre))
    except AuthenticationNeededError as ane:
        return DespResponse(data=response, error=str(ane), http_status=401)


@router.put(
    "/post/moderate/{post_id}",
    response_model=BaseDespResponse[DiscussionPostResponse],
    summary="This method moderate an existing post",
    response_description="Returns the updated post",
    tags=["discussion"],
    openapi_extra=openapi_extra(secured=True, internal=True),
)
async def moderate_post(post_id: str, request_body: EditPostBody) -> BaseDespResponse[DiscussionPostResponse]:
    """Use this method to moderate and edit an existing post"""
    user: DespUser = get_current_user()
    response = {}
    try:
        await ensure_user(user)
        original_post = await get_discourse_post(post_id)
        response = await edit_discourse_post(
            post_id,
            request_body.text,
        )
        await send_email_to_mq(
            notification_type=NotificationTemplate.ASSET_MODERATION_REJECTED,
            user_email=user.profile.email,
            subject="Post refused by moderation",
            message=f"Post has been refused by the moderation: {original_post.cooked}",
            user_id=user.id,
        )
        query_result = DiscussionPostResponse(**(response.model_dump()))
        return DespResponse(data=query_result.model_dump(mode="json"))
    except (DiscourseUnavailableError, DiscourseResourceUnavailableError):
        return DespResponse(data=response, error=DEFAULT_INTERNAL_ERROR_MESSAGE)
    except DiscourseRequestError as dre:
        return DespResponse(data=response, error=str(dre))
    except AuthenticationNeededError as ane:
        return DespResponse(data=response, error=str(ane), http_status=401)


@router.get(
    "/topic/{topic_id}",
    response_model=BaseDespResponse[DiscussionTopicResponse],
    summary="This method returns all posts of the topic",
    response_description="list of posts",
    tags=["discussion"],
    openapi_extra=openapi_extra(secured=False, roles=["user"], internal=False),
)
async def get_topic(topic_id: str) -> BaseDespResponse[DiscussionTopicResponse]:
    """Get all posts of the topic"""
    logger.info("Getting all the topics")
    response = {}
    try:
        # everyone can see the discussions
        (topic, posts) = await get_discourse_posts(topic_id)
        logger.debug("Get topic response %s", response)
        query_result = DiscussionTopicResponse.from_reply(topic, posts)
        return DespResponse(data=query_result.model_dump(mode="json"))
    except (DiscourseUnavailableError, DiscourseResourceUnavailableError):
        return DespResponse(data=response, error=DEFAULT_INTERNAL_ERROR_MESSAGE)
    except DiscourseRequestError as dre:
        return DespResponse(data=response, error=str(dre))
    except AuthenticationNeededError as ane:
        return DespResponse(data=response, error=str(ane), http_status=401)


MIN_TITLE_SIZE_IN_CHAR = 15
MIN_CONTENT_SIZE_IN_CHAR = 20


@router.post(
    "/topic",
    response_model=BaseDespResponse[DiscussionPostResponse],
    summary="This method creates a new topic",
    response_description="Returns a topic",
    tags=["discussion"],
    openapi_extra=openapi_extra(secured=True, roles=["user"], internal=False),
)
async def create_topic(topic_request_body: CreateTopicBody) -> BaseDespResponse[DiscussionPostResponse]:
    """Use this method to create a new topic
    Arg:
        topic_request_body (CreateTopicBody)

    """
    logger.info("Creating topic")
    user: DespUser = get_current_user()
    discourse_username = user.username
    response = {}
    if len(topic_request_body.title) < MIN_TITLE_SIZE_IN_CHAR:
        logger.error("Title is too short '%s'", topic_request_body.title)
        return DespResponse(data=response, error=TITLE_TOO_SHORT, http_status=400)
    if len(topic_request_body.text) < MIN_CONTENT_SIZE_IN_CHAR:
        logger.error("Text is too short '%s'", topic_request_body.text)
        return DespResponse(data=response, error=CONTENT_TOO_SHORT, http_status=400)
    try:
        await ensure_user(user)
        # Getting the id of the category associated to the asset
        asset_category_id = await get_category_asset(topic_request_body.asset_id)
        if asset_category_id is None:
            return DespResponse(
                data={
                    "Error": f"Topic creation Failed. Category_id for asset {topic_request_body.asset_id} is missing."
                },
                http_status=500,
            )
        logger.debug("Found a category %s for asset %s", asset_category_id, topic_request_body.asset_id)
        post = await create_discourse_topic(
            discourse_username, asset_category_id, topic_request_body.title, topic_request_body.text
        )
        query_result = DiscussionPostResponse.from_reply(post)
        await send_topic_to_moderation(post.topic_id, topic_request_body.title, user)
        await send_post_to_moderation(query_result, topic_request_body.text, user)
        logger.info("Topic created")

        if str(topic_request_body.asset_id) == DISCOURSE_POST_CATEGORY_UUID:
            # This is a post, send notification to the user
            await send_email_to_mq(
                notification_type=NotificationTemplate.GENERIC,
                user_email=user.profile.email,
                subject="New Post Created",
                message=(f"A new post '{topic_request_body.title}' has been created."),
                user_id=user.id,
            )
        else:
            # This is an asset-related topic, notify the asset owner
            owner_user_id = await _get_asset_owner(topic_request_body.asset_id)
            owner_mail = await get_mail_from_desp_user_id(owner_user_id)
            asset = await get_asset(topic_request_body.asset_id)
            await send_email_to_mq(
                notification_type=NotificationTemplate.GENERIC,
                user_email=owner_mail,
                subject="New Topic created for your asset",
                message=(
                    f"A new topic '{topic_request_body.title}' has been created "
                    f"for your asset '{asset['data']['public']['name']}'"
                ),
                user_id=user.id,
            )

        return DespResponse(data=query_result.model_dump(mode="json"))
    except (DiscourseUnavailableError, DiscourseResourceUnavailableError):
        return DespResponse(data=response, error=DEFAULT_INTERNAL_ERROR_MESSAGE)
    except DiscourseRequestError as dre:
        return DespResponse(data=response, error=str(dre), http_status=400)
    except AuthenticationNeededError as ane:
        return DespResponse(data=response, error=str(ane), http_status=401)


@router.delete(
    "/topic/{topic_id}",
    response_model=BaseDespResponse[DiscussionPostResponse],
    summary="This method deletes a topic",
    response_description="Returns a success message if deleted",
    tags=["discussion"],
    openapi_extra=openapi_extra(secured=True, roles=["user"], internal=False),
)
async def delete_topic(topic_id: str) -> BaseDespResponse[DiscussionPostResponse]:
    """Delete a topic from Discourse"""
    logger.info("Deleting topic %s", topic_id)
    user: DespUser = get_current_user()
    response = {}

    try:
        # Ensure user is allowed to delete
        await ensure_user(user)

        # Get topic details to check ownership
        topic = await get_discourse_topic(topic_id)

        # Check if the current user is the owner or admin
        current_user_roles = await get_current_user_roles()
        is_admin = "admin" in [role.lower() for role in current_user_roles]
        logger.debug("is_admin: %s", is_admin)
        logger.debug("topic.username: %s", topic.username)
        if topic.username != user.username and not is_admin:
            message = "Only the topic owner or admin can delete the topic."
            logger.error(message)
            return DespResponse(data={}, error=message, http_status=403)

        # Call discourse API to delete the topic
        await delete_discourse_topic(topic_id)

        logger.info("Topic %s deleted", topic_id)
        return DespResponse(data={"message": "Topic deleted successfully"})

    except (DiscourseUnavailableError, DiscourseResourceUnavailableError):
        return DespResponse(data=response, error=DEFAULT_INTERNAL_ERROR_MESSAGE, http_status=500)
    except DiscourseRequestError as dre:
        return DespResponse(data=response, error=str(dre), http_status=400)
    except AuthenticationNeededError as ane:
        return DespResponse(data=response, error=str(ane), http_status=401)


@router.delete(
    "/topic/moderate/{topic_id}",
    response_model=BaseDespResponse[DiscussionPostResponse],
    summary="This method moderate a topic",
    response_description="Returns a success message if moderate",
    tags=["discussion"],
    openapi_extra=openapi_extra(secured=True, roles=["admin"], internal=True),
)
async def moderate_topic(topic_id: str) -> BaseDespResponse[DiscussionPostResponse]:
    """Moderate a topic from Discourse"""
    logger.info("Moderate topic %s", topic_id)
    user: DespUser = get_current_user()
    response = {}

    try:
        # Ensure user is allowed to moderate
        await ensure_user(user)

        # Call discourse API to delete the topic
        response = await get_discourse_topic(topic_id)
        await delete_discourse_topic(topic_id)

        await send_email_to_mq(
            notification_type=NotificationTemplate.ASSET_MODERATION_REJECTED,
            user_email=user.profile.email,
            subject="Topic refused by moderation",
            message=f"Topic has been refused by the moderation: {response.title}",
            user_id=user.id,
        )

        logger.info("Topic %s moderated", topic_id)
        return DespResponse(data={"message": "Topic moderated successfully"})

    except (DiscourseUnavailableError, DiscourseResourceUnavailableError):
        return DespResponse(data=response, error=DEFAULT_INTERNAL_ERROR_MESSAGE, http_status=500)
    except DiscourseRequestError as dre:
        return DespResponse(data=response, error=str(dre), http_status=400)
    except AuthenticationNeededError as ane:
        return DespResponse(data=response, error=str(ane), http_status=401)
