import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models


class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField(unique=True)
    code = models.TextField(unique=True)
    icon = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "branches"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Announcement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.TextField()
    message = models.TextField()
    attachment_url = models.TextField(null=True, blank=True)
    attachment_name = models.TextField(null=True, blank=True)
    target_branch = models.ForeignKey(
        Branch,
        db_column="target_branch_id",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
    )
    created_by = models.ForeignKey(
        "User",
        db_column="created_by",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "announcements"
        ordering = ["-created_at"]


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    email = models.TextField(unique=True)
    password_hash = models.TextField()
    role = models.TextField(default="student")
    branch = models.ForeignKey(
        Branch,
        db_column="branch_id",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
    )
    semester = models.IntegerField(null=True, blank=True)
    bio = models.TextField(blank=True, default="")
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "users"


class Subject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, db_column="branch_id", on_delete=models.DO_NOTHING)
    name = models.TextField()
    slug = models.TextField()

    class Meta:
        managed = False
        db_table = "subjects"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Note(models.Model):
    SOURCE_TEACHER = "teacher"
    SOURCE_AI = "ai"
    SOURCE_CHOICES = (
        (SOURCE_TEACHER, "Teacher upload"),
        (SOURCE_AI, "AI study material"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(Subject, on_delete=models.DO_NOTHING)
    title = models.TextField()
    description = models.TextField(blank=True, default="")
    file_url = models.TextField(null=True, blank=True)
    file_name = models.TextField(null=True, blank=True)
    source_type = models.TextField(
        choices=SOURCE_CHOICES,
        default=SOURCE_TEACHER,
    )
    created_by = models.ForeignKey(
        User, db_column="created_by", null=True, blank=True, on_delete=models.DO_NOTHING
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "notes"
        ordering = ["-created_at"]


class Tool(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        Branch, db_column="branch_id", null=True, blank=True, on_delete=models.DO_NOTHING
    )
    subject = models.ForeignKey(
        Subject, null=True, blank=True, on_delete=models.DO_NOTHING
    )
    name = models.TextField()
    slug = models.TextField(unique=True)
    description = models.TextField(blank=True, default="")
    category = models.TextField()
    route = models.TextField()
    icon = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "tools"
        ordering = ["name"]


class Book(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    title = models.TextField()
    author = models.TextField(blank=True, default="")
    subject = models.TextField(blank=True, default="")
    branch = models.ForeignKey(
        Branch, db_column="branch_id", null=True, blank=True, on_delete=models.DO_NOTHING
    )
    action = models.TextField(
        default="borrow",
        choices=(("borrow", "Borrow"), ("exchange", "Exchange"), ("donate", "Donate")),
    )
    location = models.TextField(blank=True, default="")
    available_until = models.DateField(null=True, blank=True)
    status = models.TextField(default="available")
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "books"
        ordering = ["-created_at"]


class BookRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(Book, on_delete=models.DO_NOTHING)
    requester = models.ForeignKey(
        User, db_column="requester_id", on_delete=models.DO_NOTHING
    )
    status = models.TextField(default="pending")
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "book_requests"
        ordering = ["-created_at"]


class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    skill_name = models.TextField()
    type = models.TextField(choices=(("teach", "Teach"), ("learn", "Learn")))
    level = models.TextField(
        default="beginner",
        choices=(("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")),
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "skills"
        ordering = ["-created_at"]


class SkillRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    skill = models.ForeignKey(Skill, on_delete=models.DO_NOTHING)
    requester = models.ForeignKey(
        User, db_column="requester_id", on_delete=models.DO_NOTHING
    )
    offered_skill = models.ForeignKey(
        Skill,
        db_column="offered_skill_id",
        null=True,
        blank=True,
        related_name="offered_requests",
        on_delete=models.DO_NOTHING,
    )
    message = models.TextField(blank=True, default="")
    status = models.TextField(default="pending")
    requester_completed_at = models.DateTimeField(null=True, blank=True)
    owner_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "skill_requests"
        ordering = ["-created_at"]


class SkillFeedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(SkillRequest, on_delete=models.DO_NOTHING)
    reviewer = models.ForeignKey(
        User, db_column="reviewer_id", on_delete=models.DO_NOTHING
    )
    reviewee = models.ForeignKey(
        User,
        db_column="reviewee_id",
        related_name="received_feedback",
        on_delete=models.DO_NOTHING,
    )
    rating = models.IntegerField()
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "skill_feedback"
        ordering = ["-created_at"]


class HelpRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    branch = models.ForeignKey(
        Branch, db_column="branch_id", null=True, blank=True, on_delete=models.DO_NOTHING
    )
    title = models.TextField()
    description = models.TextField()
    status = models.TextField(default="open")
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "help_requests"
        ordering = ["-created_at"]


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        User, db_column="created_by", on_delete=models.DO_NOTHING
    )
    title = models.TextField()
    description = models.TextField()
    difficulty = models.TextField(default="beginner")
    required_skills = ArrayField(models.TextField(), default=list)
    branches = ArrayField(models.TextField(), default=list)
    attachment_url = models.TextField(null=True, blank=True)
    attachment_name = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "projects"
        ordering = ["-created_at"]


class Favorite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    tool = models.ForeignKey(Tool, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "favorites"


class ToolHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.DO_NOTHING)
    tool = models.ForeignKey(Tool, on_delete=models.DO_NOTHING)
    used_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "tool_history"
        ordering = ["-used_at"]
