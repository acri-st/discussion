"""Auth service"""

from typing import NoReturn

from msfwk.exceptions import DespGenericError
from msfwk.request import HttpClient
from msfwk.utils.logging import get_logger

from discussion.models.constants import AUTH_ERROR, HTTP_STATUS_OK, HTTP_STATUS_UNAUTHORIZED
from discussion.models.exceptions import DiscourseRequestError, UserNotLoggedInError

logger = get_logger("auth_service")


async def get_mail_from_desp_user_id(desp_user_id: str) -> str:
    """Get the mail from the desp user id

    Args:
        desp_user_id (str): id of the desp user

    Returns:
        str: mail of the desp user
    """
    try:
        http_client = HttpClient()
        async with (
            http_client.get_service_session("auth") as http_session,
            http_session.get(f"/profile/{desp_user_id}") as response,
        ):
            if response.status != 200:  # noqa: PLR2004
                logger.error(await response.json())
            else:
                logger.info("Mail fetched !")

            response_content = await response.json()
            logger.info("Reponse from the service: %s", response_content)

            return response_content["data"]["profile"]["email"]

    except Exception as E:
        msg = f"Exception while contacting auth service : {E}"
        logger.exception(msg)
        raise DespGenericError(
            status_code=500,
            message=f"Could not call auth service : {E}",
            code=AUTH_ERROR,
        ) from None


async def get_current_user_roles() -> list[str]:
    """Get the current user's roles from the auth service.

    Returns
        list[str]: List of roles assigned to the current user
    Raises:
        AuthenticationNeededError: If the user is not logged in
        DiscourseRequestError: If there's an error retrieving the roles
    """

    def _handle_unauthorized() -> NoReturn:
        logger.error(unauthorized_msg)
        raise UserNotLoggedInError(unauthorized_msg)

    logger.debug("Getting current user roles")
    url = "/profile"
    error_msg = "Failed to get current user roles"
    unauthorized_msg = "User is not logged in"

    try:
        http_client = HttpClient()
        async with (
            http_client.get_service_session("auth") as session,
            session.get(url) as response,
        ):
            if response.status == HTTP_STATUS_UNAUTHORIZED:
                _handle_unauthorized()
            if response.status == HTTP_STATUS_OK:
                logger.debug("User is logged in")
                response_json = await response.json()
                return response_json["data"]["roles"]
    except Exception as e:
        logger.exception(error_msg)
        raise DiscourseRequestError(error_msg) from e
