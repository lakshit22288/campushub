import uuid
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import IntegrityError
from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve, reverse

from portal import features
from portal.forms import SkillForm


class SkillSwapRequestWorkflowTests(SimpleTestCase):
    def make_request(self, path, user_id, data=None):
        request = RequestFactory().post(path, data=data or {})
        SessionMiddleware(lambda current_request: None).process_request(request)
        request.session["campushub_user"] = {"id": str(user_id)}
        request.session.save()
        request._messages = FallbackStorage(request)
        return request

    def render_skill_swap(self, current_user, skill_request):
        request = SimpleNamespace(
            id=uuid.uuid4(),
            skill=SimpleNamespace(
                id=uuid.uuid4(),
                skill_name="Python",
                user_id=skill_request.skill.user_id,
                user=SimpleNamespace(id=skill_request.skill.user_id, name="Teacher", email="teacher@example.edu"),
            ),
            requester_id=skill_request.requester_id,
            requester=SimpleNamespace(id=skill_request.requester_id, name="Learner", email="learner@example.edu"),
            offered_skill=None,
            message=skill_request.message,
            status=skill_request.status,
            requester_completed_at=None,
            owner_completed_at=None,
        )
        context = {
            "campushub_user": current_user,
            "current_user_id": str(current_user.id),
            "form": SkillForm(),
            "listings": [],
            "listing_count": 0,
            "own_skills": [],
            "own_teach_skills": [],
            "branches": [],
            "query": "",
            "selected_type": "",
            "selected_level": "",
            "selected_branch": "",
            "requests": [request],
            "pending_received_count": int(skill_request.status == "pending"),
            "feedback": [],
            "feedback_ids": set(),
        }
        return get_template("portal/skillswap.html").render(context)

    @patch("portal.features.SkillRequest.objects.create")
    @patch("portal.features.get_object_or_404")
    @patch("portal.features.User.objects.filter")
    def test_learning_request_is_saved_and_redirects_to_the_visible_inbox(
        self,
        user_filter,
        get_skill,
        create_request,
    ):
        requester_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        skill = SimpleNamespace(id=uuid.uuid4(), user_id=owner_id, type="teach")
        user_filter.return_value.first.return_value = SimpleNamespace(id=requester_id)
        get_skill.return_value = skill
        request = self.make_request(
            reverse("request_skill", args=[skill.id]),
            requester_id,
            {"message": "Could you help me get started?"},
        )

        with patch("portal.features.transaction.atomic", return_value=nullcontext()):
            response = features.request_skill(request, skill.id)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{reverse('skillswap')}#my-requests")
        create_request.assert_called_once()
        self.assertEqual(create_request.call_args.kwargs["skill"], skill)
        self.assertEqual(create_request.call_args.kwargs["requester"].id, requester_id)
        self.assertEqual(create_request.call_args.kwargs["message"], "Could you help me get started?")
        self.assertEqual(create_request.call_args.kwargs["status"], "pending")
        self.assertIn("Your learning request has been sent.", [str(message) for message in request._messages])

    @patch("portal.features.logger.exception")
    @patch("portal.features.SkillRequest.objects.filter")
    @patch("portal.features.SkillRequest.objects.create", side_effect=IntegrityError("unexpected constraint"))
    @patch("portal.features.get_object_or_404")
    @patch("portal.features.User.objects.filter")
    def test_unexpected_request_save_failure_is_not_reported_as_a_duplicate(
        self,
        user_filter,
        get_skill,
        create_request,
        request_filter,
        logger_exception,
    ):
        requester_id = uuid.uuid4()
        skill = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), type="teach")
        user_filter.return_value.first.return_value = SimpleNamespace(id=requester_id)
        get_skill.return_value = skill
        request_filter.return_value.exists.return_value = False
        request = self.make_request(reverse("request_skill", args=[skill.id]), requester_id)

        with patch("portal.features.transaction.atomic", return_value=nullcontext()):
            features.request_skill(request, skill.id)

        self.assertIn(
            "We could not send your request. Please try again.",
            [str(message) for message in request._messages],
        )
        self.assertNotIn(
            "You already have an active request for this skill.",
            [str(message) for message in request._messages],
        )
        logger_exception.assert_called_once_with("Could not save a SkillSwap learning request")

    def test_pending_request_shows_message_and_accept_action_without_sharing_email(self):
        owner_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        html = self.render_skill_swap(
            SimpleNamespace(id=owner_id),
            SimpleNamespace(
                skill=SimpleNamespace(user_id=owner_id),
                requester_id=requester_id,
                status="pending",
                message="I would love to learn this.",
            ),
        )

        self.assertIn("YOUR EXCHANGE INBOX", html)
        self.assertIn("I would love to learn this.", html)
        self.assertIn("Accept request", html)
        self.assertNotIn("mailto:", html)

    def test_accepted_request_unlocks_private_email_contact_for_participants(self):
        owner_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        html = self.render_skill_swap(
            SimpleNamespace(id=owner_id),
            SimpleNamespace(
                skill=SimpleNamespace(user_id=owner_id),
                requester_id=requester_id,
                status="accepted",
                message="I would love to learn this.",
            ),
        )

        self.assertIn(
            'href="https://mail.google.com/mail/?view=cm&amp;fs=1&amp;to=learner%40example.edu&amp;su=CampuZHub%20SkillSwap%20-%20Python"',
            html,
        )
        self.assertIn('target="_blank" rel="noopener noreferrer"', html)
        self.assertIn("Your SkillSwap request is accepted.", html)
        self.assertIn("Confirm completed", html)

    def test_learner_can_email_the_teacher_after_acceptance(self):
        owner_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        html = self.render_skill_swap(
            SimpleNamespace(id=requester_id),
            SimpleNamespace(
                skill=SimpleNamespace(user_id=owner_id),
                requester_id=requester_id,
                status="accepted",
                message="I would love to learn this.",
            ),
        )

        self.assertIn(
            'href="https://mail.google.com/mail/?view=cm&amp;fs=1&amp;to=teacher%40example.edu&amp;su=CampuZHub%20SkillSwap%20-%20Python"',
            html,
        )
        self.assertIn('target="_blank" rel="noopener noreferrer"', html)
        self.assertIn("Email Teacher", html)
