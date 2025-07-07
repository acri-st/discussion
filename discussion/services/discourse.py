"""Discourse service"""

import random
import re
from http.client import FORBIDDEN, NOT_FOUND, TOO_MANY_REQUESTS, UNPROCESSABLE_ENTITY
from typing import TYPE_CHECKING, Any
from uuid import UUID

import aiohttp
from msfwk import database
from msfwk.context import current_config
from msfwk.models import DespUser
from msfwk.utils.logging import get_logger
from sqlalchemy import Result
from sqlalchemy.exc import IntegrityError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from discussion.models.exceptions import (
    AuthenticationNeededError,
    DiscourseAuthenticationError,
    DiscourseRequestError,
    DiscourseResourceUnavailableError,
    DiscourseUnavailableError,
)
from discussion.models.interfaces import DiscourseCategory, DiscoursePost, DiscourseTopic

log = get_logger("discussion")


def get_discourse_header(username: str = "system") -> dict:
    """Build the header for the requests"""
    discourse_config = get_discussion_config()
    return {"Api-Key": discourse_config["api_key"], "Api-Username": username, "Accept": "application/json"}


def get_discussion_config() -> dict:
    """Return a default config for this service"""
    return current_config.get().get("services", {}).get("discussion", {"ssl_check": True})


def is_a_5xx_error(status: str) -> bool:
    """Check that we haven't a 500 from the service"""
    rest_of_division = 5
    return int(status / 100) == rest_of_division


async def handle_response_error(response: aiohttp.ClientResponse, message: str) -> None:
    """Check that we don't have a strong issue in the call"""
    discourse_config = get_discussion_config()
    if is_a_5xx_error(response.status):
        log.error(
            "Something is wrong with the Discourse app %s %s %s",
            response.url,
            response.status,
            await response.text(),
        )
        log.error(message)
        raise DiscourseUnavailableError(message)
    if response.status == FORBIDDEN:
        error = f"Failed to authenticate on discourse during {message}"
        log.error(
            "Authentication issue on %s using key %s",
            discourse_config["discourse_host"],
            discourse_config["api_key"],
        )
        raise DiscourseAuthenticationError(error)
    if response.status == UNPROCESSABLE_ENTITY:
        error = f"Provided parameters are not matching expectation during {message}"
        log.error(error)
        json_response = await response.json()
        log.error("Check parameter for %s", json_response["errors"])
        raise DiscourseRequestError("-".join(json_response["errors"]))
    if response.status == TOO_MANY_REQUESTS:
        error = f"Too many request during {message}"
        log.error(error)
        json_response = await response.json()
        raise DiscourseRequestError("-".join(json_response["errors"]))


async def get_category_asset(asset_id: UUID) -> UUID | None:
    """Retrieve the category id from the database based on the asset_id"""
    db_session: AsyncSession
    try:
        # First the insertion in database
        async with database.get_schema().get_async_session() as db_session:
            discourse_table = database.get_schema().tables["Discourses"]
            result = await db_session.execute(discourse_table.select().where(discourse_table.c.assetId == asset_id))
            record: dict | None = get_first_record(result)
            log.debug("Discourse category records %s", record)
            return record.get("categoryId") if record is not None else None
    except IntegrityError as ie:
        log.exception("Failed to retrieve category for asset %s", asset_id, exc_info=ie)
        return None


def get_first_record(result: Result) -> dict[Any, Any] | None:
    """_summary_

    Args:
        result (_type_): _description_

    Returns:
        dict[Any, Any] | None: _description_
    """
    first = result.first()
    return dict(first._mapping) if first is not None else None  # noqa: SLF001


async def set_category_asset(category_id: int, asset_id: UUID) -> int | None:
    """Retrieve the category id from the database based on the asset_id"""
    db_session: AsyncSession
    try:
        # First the insertion in database
        async with database.get_schema().get_async_session() as db_session:
            discourse_table = database.get_schema().tables["Discourses"]
            await db_session.execute(discourse_table.insert().values(categoryId=category_id, assetId=asset_id))
            log.debug("Asset %s update with a category", asset_id)
            await db_session.commit()
    except IntegrityError as ie:
        log.exception("Failed to store category for asset %s", asset_id, exc_info=ie)
        return None


async def ensure_user(desp_user: DespUser) -> None:
    """Ensure that the current user exists

    Args:
        desp_user (DespUser): the user in the system
    """
    if desp_user is None:
        message = "You need to be logged in in order to publish on forum"
        log.error(message)
        raise AuthenticationNeededError(message)
    log.info("Checking user %s", desp_user.id)
    discourse_config = get_discussion_config()
    payload = {
        "name": desp_user.displayName,
        "email": f"{desp_user.id}@eu.space",
        "password": "#despAAS2024",
        "username": desp_user.username,
        "active": "true",
        "approved": "true",
    }
    log.info(
        "Ensuring user with discourse_config: %s, ssl_check: %s",
        discourse_config,
        discourse_config.get("ssl_check", "MISSING CONFIG VALUE"),
    )
    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            headers=get_discourse_header(),
            connector=aiohttp.TCPConnector(verify_ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.post("/users.json", json=payload) as response,
    ):
        log.debug("Discourse call returned %s", response.status)
        # Will throw if there is an error
        await handle_response_error(response, "category retrieval")
        # If we don't get an error we have either already the user in the discourse system
        # Or we just created it. We are always impersonating the user so we don't need it


async def get_discourse_category(category: UUID | None, asset_id: UUID) -> DiscourseCategory:
    """Get category data"""
    discourse_config = get_discussion_config()
    log.info("Getting category %s asset %s", category, asset_id)
    if category is None:
        return await create_category(asset_id)
    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            headers=get_discourse_header(),
            connector=aiohttp.TCPConnector(ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.get(f"/c/{category}/show.json") as response,
    ):
        log.debug("Discourse call returned %s", response.status)
        # Will throw if there is an error
        await handle_response_error(response, "category retrieval")
        if response.status == NOT_FOUND:
            return await create_category(asset_id)
        category_response = await response.json()
        log.debug("Category response %s %s", response.status, category_response)
        return DiscourseCategory(**category_response["category"])


async def create_category(asset_id: UUID) -> DiscourseCategory:
    """Create a discourse category with the category name"""
    log.info("Creating category for %s", asset_id)
    discourse_config = get_discussion_config()
    num: int = int(random.random() * (10**6))  # noqa: S311
    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            headers=get_discourse_header(),
            connector=aiohttp.TCPConnector(ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.post("/categories.json", json={"name": f"{num}_{asset_id}"}) as response,
    ):
        log.debug("Discourse call returned %s", response.status)
        if response.status not in (200, 201):
            await handle_response_error(response, "category creation")
        category_response = await response.json()
    log.debug("category_response %s", category_response)
    if "errors" in category_response:
        raise DiscourseRequestError("-".join(category_response["errors"]))
    discourse_category = DiscourseCategory(**category_response["category"])
    # Store the relationship in database
    await set_category_asset(discourse_category.id, asset_id)
    return discourse_category


async def get_discourse_topics(slug: str, category_id: int) -> list[DiscourseTopic]:
    """To get all topics (and other data) from a specific category"""
    discourse_config = get_discussion_config()
    log.info("Getting topics for slug:%s category:%s", slug, category_id)

    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            connector=aiohttp.TCPConnector(ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.get(f"/c/{slug}/{category_id}.json") as response,
    ):
        if response.status not in (200, 201):
            if response.status == NOT_FOUND:
                log.error("Category %s does not exist: %s / %s", category_id, response.status, await response.text())
                raise DiscourseResourceUnavailableError
            handle_response_error(response, "Getting topics")

        data = await response.json()
        log.debug("Category Topics: %s", data)

        user_lookup = {user["id"]: user["username"] for user in data.get("users", [])}
        topics = data["topic_list"]["topics"]
        # Filter out default messages
        topics = [topic for topic in topics if not check_default_message(topic["title"])]

        enriched_topics = []
        for topic in topics:
            # Default username to None
            username = None

            for poster in topic.get("posters", []):
                if "Original Poster" in poster.get("description", ""):
                    user_id = poster.get("user_id")
                    username = user_lookup.get(user_id)
                    break

            topic["username"] = username
            enriched_topics.append(DiscourseTopic(**topic))
        log.debug("Enriched topic: %s", enriched_topics)

        return enriched_topics


def check_default_message(s: str) -> bool:
    """Check if the string follows the pattern: "About the <digits>_<UUID> category"

    Args:
        s (str): The input string to check.

    Returns:
        bool: True if the input matches the pattern, False otherwise.
    """
    pattern = r"About the \d+_[a-f0-9\-]+ category"
    return bool(re.match(pattern, s))


async def create_discourse_topic(username: str, category_id: UUID, title: str, content: str) -> DiscoursePost:
    """Creates a new topic"""
    discourse_config = get_discussion_config()
    log.info("Creating discourse topic on category %s for %s", category_id, username)

    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            headers=get_discourse_header(username),
            connector=aiohttp.TCPConnector(ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.post(
            "/posts.json",
            json={"category": str(category_id), "title": title, "raw": content},
        ) as response,
    ):
        log.debug("Discourse call returned %s", response.status)
        if response.status not in (200, 201):
            await handle_response_error(response, "Topic creation")
        topic_response = await response.json()
        log.debug("topic_response %s", topic_response)
        if "error" in topic_response:
            raise DiscourseRequestError("-".join(topic_response["error"]))
        return DiscoursePost(**topic_response)


async def create_discourse_post(username: str, topic_id: str, text: str) -> dict:
    """Use this method to create a new post in a topic"""
    discourse_config = get_discussion_config()
    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            headers=get_discourse_header(username),
            connector=aiohttp.TCPConnector(ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.post("/posts.json", json={"topic_id": topic_id, "raw": text}) as response,
    ):
        if response.status not in (200, 201):
            await handle_response_error(response, "Post creation")

        return await response.json()


async def get_discourse_posts(topic_id: str) -> tuple[DiscourseTopic, list[DiscoursePost]]:
    """Use this method to get the list of post for a topic"""
    discourse_config = get_discussion_config()
    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            headers=get_discourse_header(),
            connector=aiohttp.TCPConnector(ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.get(f"/t/{topic_id}.json", params={"print": "true"}) as response,
    ):
        if response.status not in (200, 201):
            await handle_response_error(response, "Post listing")

        topic = await response.json()
        log.debug("topic for get_discourse_posts %s", topic)

        # Extract username from topic creator
        if "details" in topic and "created_by" in topic["details"]:
            creator = topic["details"]["created_by"]
            topic["username"] = creator.get("username")

        return (DiscourseTopic(**topic), [DiscoursePost(**post) for post in topic["post_stream"]["posts"]])


async def get_discourse_topic(topic_id: str) -> DiscourseTopic:
    """Use this method to get a topic"""
    discourse_config = get_discussion_config()
    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            headers=get_discourse_header(),
            connector=aiohttp.TCPConnector(ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.get(f"/t/{topic_id}.json") as response,
    ):
        if response.status not in (200, 201):
            await handle_response_error(response, "Fetching topic")

        topic_data = await response.json()

        # Get creator info from details.created_by
        if "details" in topic_data and "created_by" in topic_data["details"]:
            creator = topic_data["details"]["created_by"]
            topic_data["username"] = creator.get("username")

        return DiscourseTopic(**topic_data)


async def get_discourse_post(post_id: str) -> DiscoursePost:
    """Fetch a specific post by its ID from Discourse."""
    discourse_config = get_discussion_config()
    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            headers=get_discourse_header(),
            connector=aiohttp.TCPConnector(ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.get(f"/posts/{post_id}.json") as response,
    ):
        if response.status not in (200, 201):
            await handle_response_error(response, "Fetching post")

        post_data = await response.json()
        return DiscoursePost(**post_data)


async def edit_discourse_post(post_id: str, updated_content: str) -> DiscoursePost:
    """Modify a Discourse post with the given post_id and updated content."""
    discourse_config = get_discussion_config()
    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            headers=get_discourse_header(),
            connector=aiohttp.TCPConnector(ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.put(f"/posts/{post_id}.json", json={"raw": updated_content}) as response,
    ):
        if response.status not in (200, 201):
            await handle_response_error(response, "Post modification")

        post_data = (await response.json()).get("post")
        return DiscoursePost(**post_data)


async def delete_discourse_topic(topic_id: str) -> None:
    """Deletes a Discourse topic with the given topic_id."""
    discourse_config = get_discussion_config()
    log.info("Deleting discourse topic with ID %s", topic_id)

    async with (
        aiohttp.ClientSession(
            discourse_config["discourse_host"],
            headers=get_discourse_header(),
            connector=aiohttp.TCPConnector(ssl=discourse_config.get("ssl_check", True)),
        ) as session,
        session.delete(f"/t/{topic_id}.json") as response,
    ):
        if response.status not in (200, 201):
            await handle_response_error(response, "Topic deletion")

        log.info("Topic %s successfully deleted", topic_id)
