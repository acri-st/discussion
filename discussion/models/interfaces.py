"""Interfaces for the discussion service"""

from uuid import UUID

from pydantic import BaseModel


class DiscourseCategory(BaseModel):
    """Object representing the Category returned by Discourse"""

    id: int
    name: str
    color: str
    text_color: str
    slug: str
    topic_count: int
    post_count: int
    position: int
    description: str | None
    description_text: str | None
    description_excerpt: str | None
    topic_url: str | None
    read_restricted: bool
    permission: int | None
    topic_template: str | None
    has_children: bool | None
    sort_order: str | None
    sort_ascending: str | None
    show_subcategory_list: bool
    num_featured_topics: int
    default_view: str | None
    subcategory_list_style: str
    default_top_period: str
    default_list_filter: str
    minimum_required_tags: int
    navigate_to_first_post_after_read: bool
    custom_fields: dict
    allowed_tags: list[str]
    allowed_tag_groups: list[str]
    allow_global_tags: bool
    read_only_banner: str | None
    form_template_ids: list[str]
    auto_close_hours: str | None
    auto_close_based_on_last_post: bool
    mailinglist_mirror: bool
    all_topics_wiki: bool
    allow_unlimited_owner_edits_on_first_post: bool
    allow_badges: bool
    topic_featured_link_allowed: bool
    search_priority: int
    default_slow_mode_seconds: str | None
    uploaded_logo: str | None
    uploaded_logo_dark: str | None
    uploaded_background: str | None
    uploaded_background_dark: str | None
    required_tag_groups: list[str]


class DiscourseTopic(BaseModel):
    """Object representing the topics returned from discourse API"""

    id: int
    title: str
    fancy_title: str
    slug: str
    posts_count: int
    reply_count: int
    highest_post_number: int
    image_url: str | None
    created_at: str
    last_posted_at: str | None
    bumped: bool = False
    bumped_at: str | None = None
    archetype: str
    unseen: bool = False
    pinned: bool
    unpinned: str | None
    visible: bool
    closed: bool
    archived: bool
    views: int
    like_count: int
    has_summary: bool
    category_id: int
    pinned_globally: bool
    featured_link: str | None
    last_poster_username: str | None = None
    username: str | None = None


class DiscoursePost(BaseModel):
    """Object representing the posts returned from discourse API"""

    id: int
    name: str
    username: str
    avatar_template: str
    created_at: str
    cooked: str
    post_number: int
    post_type: int
    updated_at: str
    reply_count: int
    reply_to_post_number: str | None
    quote_count: int
    incoming_link_count: int
    reads: int
    readers_count: int
    score: float
    yours: bool
    topic_id: int
    topic_slug: str
    display_username: str
    primary_group_name: str | None
    flair_name: str | None
    flair_url: str | None
    flair_bg_color: str | None
    flair_color: str | None
    version: int
    can_edit: bool
    can_delete: bool
    can_recover: bool
    can_see_hidden_post: bool
    can_wiki: bool
    user_title: str | None
    bookmarked: bool
    moderator: bool
    admin: bool
    staff: bool
    user_id: int
    hidden: bool
    trust_level: int
    deleted_at: str | None
    user_deleted: bool
    edit_reason: str | None
    can_view_edit_history: bool
    wiki: bool


class CreatePostBody(BaseModel):
    """Request body for the post creation"""

    text: str


class EditPostBody(BaseModel):
    """Request body for the post edition"""

    text: str


class CreateTopicBody(BaseModel):
    """Request body for the topic creation"""

    title: str
    text: str
    asset_id: UUID


class DiscussionPostResponse(BaseModel):
    """Object returned to the UI representing a post"""

    id: int
    name: str
    username: str
    display_username: str
    user_id: int
    avatar_template: str
    created_at: str
    cooked: str
    topic_id: int

    @staticmethod
    def from_reply(discourse_post: DiscoursePost) -> "DiscussionPostResponse":
        """Return DiscussionTopicResponse from a business object"""
        return DiscussionPostResponse(
            id=discourse_post.id,
            name=discourse_post.name,
            username=discourse_post.username,
            display_username=discourse_post.display_username,
            user_id=discourse_post.user_id,
            avatar_template=discourse_post.avatar_template,
            created_at=discourse_post.created_at,
            cooked=discourse_post.cooked,
            topic_id=discourse_post.topic_id,
        )


class DiscourseQueryTopic(BaseModel):
    """Object representing the topics returned from discourse API"""

    id: int
    title: str
    fancy_title: str
    posts_count: int
    reply_count: int
    created_at: str
    category_id: int
    visible: bool
    closed: bool
    archived: bool

    @staticmethod
    def from_reply(discourse_post: DiscoursePost) -> "DiscourseQueryTopic":
        """Convert a Discourse business object into a UI expected Object"""
        return DiscourseQueryTopic(
            id=discourse_post.id,
            title=discourse_post.title,
            fancy_title=discourse_post.fancy_title,
            posts_count=discourse_post.posts_count,
            reply_count=discourse_post.reply_count,
            created_at=discourse_post.created_at,
            category_id=discourse_post.category_id,
            visible=discourse_post.visible,
            closed=discourse_post.closed,
            archived=discourse_post.archived,
        )


class DiscussionTopicResponse(BaseModel):
    """Object returned to the UI representing a topic"""

    posts: list[DiscussionPostResponse]
    id: int
    title: str
    fancy_title: str
    posts_count: int
    created_at: str
    slug: str
    category_id: int
    username: str | None = None

    @staticmethod
    def from_reply(
        discourse_topic: DiscourseTopic, posts: list[DiscoursePost] | None = None
    ) -> "DiscussionTopicResponse":
        """Return DiscussionTopicResponse from a business object"""
        if posts is None:
            posts = []
        return DiscussionTopicResponse(
            posts=[DiscussionPostResponse.from_reply(post) for post in posts],
            id=discourse_topic.id,
            title=discourse_topic.title,
            fancy_title=discourse_topic.fancy_title,
            posts_count=discourse_topic.posts_count,
            created_at=discourse_topic.created_at,
            slug=discourse_topic.slug,
            category_id=discourse_topic.category_id,
            username=discourse_topic.username,
        )


class DiscussionResponse(BaseModel):
    """Returned object on get discussion"""

    id: int
    name: str
    topics: list[DiscussionTopicResponse]

    @staticmethod
    def from_reply(
        discourse_category: DiscourseCategory, topics_response: list[DiscourseTopic]
    ) -> "DiscussionResponse":
        """Return DiscussionResponse from a business object"""
        return DiscussionResponse(
            id=discourse_category.id,
            name=discourse_category.name,
            topics=[DiscussionTopicResponse.from_reply(topic) for topic in topics_response],
        )


class TopicsReponse(BaseModel):
    """Object returned to the UI when requesting topics"""

    topics: list[DiscussionTopicResponse]
