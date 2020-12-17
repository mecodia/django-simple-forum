from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import hashlib
from datetime import datetime

STATUS = (
    ('Draft', 'Draft'),
    ('Published', 'Published'),
    ('Disabled', 'Disabled'),
)

USER_ROLES = (
    ('Admin', 'Admin'),
    ('Publisher', 'Publisher'),
)

User = settings.AUTH_USER_MODEL


# tags created for topic
class Tags(models.Model):
    title = models.CharField(max_length=50, unique=True)
    slug = models.CharField(max_length=50, unique=True)

    def get_topics(self):
        topics = Topic.objects.filter(tags__in=[self], status='Published')
        return topics


# tags created for topic
class Badge(models.Model):
    title = models.CharField(max_length=50, unique=True)
    slug = models.CharField(max_length=50, unique=True)

    def get_users(self):
        user_profile = UserProfile.objects.filter(badges__in=[self])
        return user_profile


# user profile to store no of votes available to user, badges for a topic, user roles,
class UserProfile(models.Model):
    file_prepend = "forum_user/profilepics/"
    
    user = models.ForeignKey(User)
    used_votes = models.IntegerField(default='0')
    user_roles = models.CharField(choices=USER_ROLES, max_length=10)
    badges = models.ManyToManyField(Badge)
    send_mailnotifications = models.BooleanField(default=False)

    # need to add social details for a user if we implement socail login

    def get_no_of_up_votes(self):
        user_topics = UserTopics.objects.filter(user=self.user)
        votes = 0
        for topic in user_topics:
            votes += topic.no_of_votes
        return votes

    def get_no_of_down_votes(self):
        user_topics = UserTopics.objects.filter(user=self.user)
        votes = 0
        for topic in user_topics:
            votes += topic.no_of_down_votes
        return votes

    def get_topics(self):
        topics = Topic.objects.filter(created_by=self.user)
        return topics

    def get_followed_topics(self):
        topics = UserTopics.objects.filter(user=self.user, is_followed=True)
        topics = Topic.objects.filter(id__in=topics.values_list('topic', flat=True))
        return topics

    def get_liked_topics(self):
        topics = UserTopics.objects.filter(user=self.user, is_like=True)
        topics = Topic.objects.filter(id__in=topics.values_list('topic', flat=True))
        return topics

    def get_timeline(self):
        timeline = Timeline.objects.filter(user=self.user).order_by('-created_on')
        return timeline

    def get_user_topic_tags(self):
        tags = Tags.objects.filter(id__in=self.get_topics().values_list('tags', flat=True))
        return tags

    def get_user_topic_categories(self):
        categories = ForumCategory.objects.filter(id__in=self.get_topics().values_list('category', flat=True))
        return categories
        # return []

    def get_user_suggested_topics(self):
        categories = ForumCategory.objects.filter(id__in=self.get_topics().values_list('category', flat=True))
        topics = Topic.objects.filter(category__id__in=categories.values_list('id', flat=True))
        return topics
        # return []


class ForumCategory(models.Model):
    created_by = models.ForeignKey(User)
    title = models.CharField(max_length=1000)
    is_active = models.BooleanField(default=False)
    color = models.CharField(max_length=20, default="#999999")
    is_votable = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=1000)
    description = models.TextField()
    parent = models.ForeignKey('self', blank=True, null=True)

    def get_topics(self):
        topics = Topic.objects.filter(category=self, status='Published')
        return topics

    def __str__(self):
        return self.title


class Vote(models.Model):
    TYPES = (
        ("U", "Up"),
        ("D", "Down"),
    )
    user = models.ForeignKey(User)
    type = models.CharField(choices=TYPES, max_length=1)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user

class Topic(models.Model):
    title = models.CharField(max_length=2000)
    description = models.TextField()
    created_by = models.ForeignKey(User)
    status = models.CharField(choices=STATUS, max_length=10)
    category = models.ForeignKey(ForumCategory)
    created_on = models.DateTimeField(auto_now=True)
    updated_on = models.DateTimeField(auto_now=True)
    no_of_views = models.IntegerField(default='0')
    slug = models.SlugField(max_length=1000)
    tags = models.ManyToManyField(Tags)
    no_of_likes = models.IntegerField(default='0')
    votes = models.ManyToManyField(Vote)

    def get_comments(self):
        comments = Comment.objects.filter(topic=self, parent=None)
        return comments

    def get_all_comments(self):
        comments = Comment.objects.filter(topic=self)
        return comments

    def get_last_comment(self):
        comments = Comment.objects.filter(topic=self).order_by('-updated_on').first()
        return comments

    def get_topic_users(self):
        comment_user_ids = Comment.objects.filter(topic=self).values_list('commented_by', flat=True)
        liked_users_ids = UserTopics.objects.filter(topic=self, is_like=True).values_list('user', flat=True)
        followed_users = UserTopics.objects.filter(topic=self, is_followed=True).values_list('user', flat=True)
        all_users = list(comment_user_ids) + list(liked_users_ids) + list(followed_users) + [self.created_by.id]
        users = UserProfile.objects.filter(user_id__in=set(all_users))
        return users

    # def get_total_of_votes(self):
    #     no_of_votes = self.no_of_votes + self.no_of_down_votes
    #     return no_of_votes

    def up_votes_count(self):
        return self.votes.filter(type="U").count()

    def down_votes_count(self):
        return self.votes.filter(type="D").count()  

    def __str__(self):
        return self.title      

# user followed topics
class UserTopics(models.Model):
    user = models.ForeignKey(User)
    topic = models.ForeignKey(Topic)
    is_followed = models.BooleanField(default=False)
    followed_on = models.DateField(null=True, blank=True)
    no_of_votes = models.IntegerField(default='0')
    no_of_down_votes = models.IntegerField(default='0')
    is_like = models.BooleanField(default=False)


class Comment(models.Model):
    comment = models.TextField(null=True, blank=True)
    commented_by = models.ForeignKey(User, related_name="commented_by")
    topic = models.ForeignKey(Topic, related_name="topic_comments")
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey("self", blank=True, null=True, related_name="comment_parent")
    mentioned = models.ManyToManyField(User, related_name="mentioned_users")
    votes = models.ManyToManyField(Vote)

    def get_comments(self):
        comments = self.comment_parent.all()
        return comments

    def up_votes_count(self):
        return self.votes.filter(type="U").count()

    def down_votes_count(self):
        return self.votes.filter(type="D").count()


# user activity
class Timeline(models.Model):
    content_type = models.ForeignKey(ContentType, related_name="content_type_timelines")
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    namespace = models.CharField(max_length=250, default="default", db_index=True)
    event_type = models.CharField(max_length=250, db_index=True)
    user = models.ForeignKey(User, null=True)
    data = models.TextField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        index_together = [("content_type", "object_id", "namespace"), ]
        ordering = ['-created_on']