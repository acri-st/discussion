"""Exceptions for the discussion service"""


class DiscourseRequestError(Exception):
    """Raised when we recieve an error from the Discourse application"""


class DiscourseResourceUnavailableError(Exception):
    """Raised when the requested resource cannot be identified by Discourse"""


class DiscourseUnavailableError(Exception):
    """Raised when Discourse is unavailable"""


class DiscourseAuthenticationError(Exception):
    """Raised when Discourse is unavailable"""


class AuthenticationNeededError(Exception):
    """Raised when the API is reached without a user"""


class SendPostModerationError(Exception):
    """Raised when failed to send post to moderation"""


class AssetRetrievalError(Exception):
    """Raised when failed to retrieve an asset"""


class UserNotLoggedInError(Exception):
    """Raised when user is not logged in"""
