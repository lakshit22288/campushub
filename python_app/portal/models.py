import uuid

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


class Announcement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.TextField()
    message = models.TextField()
    target_branch = models.ForeignKey(
        Branch,
        db_column="target_branch_id",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "announcements"
        ordering = ["-created_at"]
