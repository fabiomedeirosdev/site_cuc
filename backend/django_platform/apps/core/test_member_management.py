from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.policies import is_application_admin, profile_role
from apps.billing.models import LegalAcceptance
from apps.communications.models import Delegation, Event, NewsletterPreference
from apps.communications.policies import can_manage, facilitator_users
from apps.content.models import Article
from apps.content.policies import author_groups
from apps.editorial.models import EditorialGroup, Membership
from apps.editorial.policies import managed_groups


class MemberManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.developer = self.person('developer')
        self.founder = self.person('founder')
        self.group = EditorialGroup.objects.create(name='Equipe', slug='member-test')

    def person(self, role):
        user = get_user_model().objects.create_user(username=role, email=f'{role}@example.invalid')
        user.profile.community_role = role if role in {'developer', 'founder', 'columnist', 'administration', 'priest', 'deacon'} else ''
        user.profile.save()
        return user

    def test_admins_edit_and_delete_every_requested_role(self):
        for actor in [self.developer, self.founder]:
            self.client.force_authenticate(actor)
            for role in ['', 'columnist', 'administration', 'priest', 'deacon', 'founder']:
                with self.subTest(actor=actor.pk, role=role):
                    target = self.person(f'target-{actor.pk}-{role}')
                    url = f'/api/management/team/{target.pk}'
                    response = self.client.patch(url, {
                        'role': role, 'display_name': 'Nome atualizado', 'position': 4,
                        'email': f'updated-{target.pk}@example.invalid',
                        'biography': 'Uma apresentação.', 'website': 'https://example.org',
                    }, format='json')
                    self.assertEqual(response.status_code, 200, response.data)
                    target.refresh_from_db()
                    self.assertEqual(target.profile.community_role, role)
                    self.assertEqual(target.profile.display_name, 'Nome atualizado')
                    self.assertEqual(target.profile.position, 4)
                    self.assertEqual(self.client.delete(url).status_code, 204)
                    self.assertFalse(get_user_model().objects.filter(pk=target.pk).exists())

    def test_non_admins_cannot_edit_delete_or_promote_themselves(self):
        for role in ['subscriber', 'columnist', 'administration', 'priest', 'deacon']:
            actor = self.person(role)
            self.client.force_authenticate(actor)
            for endpoint in ['team', 'users']:
                url = f'/api/management/{endpoint}/{self.founder.pk}'
                self.assertEqual(self.client.patch(url, {'role': 'founder'}, format='json').status_code, 403)
                self.assertEqual(self.client.delete(url).status_code, 403)
            self.assertEqual(self.client.patch('/api/auth/me', {'community_role': 'founder'}, format='json').status_code, 400)

    def test_self_deletion_and_developer_promotion_are_protected(self):
        self.client.force_authenticate(self.founder)
        self.assertEqual(self.client.delete(f'/api/management/team/{self.founder.pk}').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/management/users/{self.developer.pk}').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/management/team/{self.founder.pk}', {'role': 'developer'}, format='json').status_code, 403)

    def test_duplicate_email_rolls_back_profile_changes(self):
        self.client.force_authenticate(self.developer)
        response = self.client.patch(f'/api/management/team/{self.founder.pk}', {
            'email': self.developer.email, 'role': 'priest', 'position': 9,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.founder.refresh_from_db()
        self.assertEqual(self.founder.profile.community_role, 'founder')
        self.assertEqual(self.founder.profile.position, 0)

    def test_deletion_preserves_history_and_disables_newsletter(self):
        target = self.person('priest')
        Membership.objects.create(user=target, group=self.group, role='columnist')
        article = Article.objects.create(author=target, group=self.group, title='Histórico', body='Texto')
        event = Event.objects.create(created_by=target, title='Encontro', starts_at=timezone.now())
        acceptance = LegalAcceptance.objects.create(user=target, version='test', source='test')
        preference = NewsletterPreference.objects.create(user=target, email=target.email, opted_in=True)
        self.client.force_authenticate(self.founder)
        self.assertEqual(self.client.delete(f'/api/management/users/{target.pk}').status_code, 204)
        for record, field in [(article, 'author_id'), (event, 'created_by_id'), (acceptance, 'user_id')]:
            record.refresh_from_db()
            self.assertIsNone(getattr(record, field))
        preference.refresh_from_db()
        self.assertFalse(preference.opted_in)
        self.assertEqual(self.client.get('/api/management/dashboard').status_code, 200)

    def test_administration_has_coordinator_scope_without_user_management(self):
        actor = self.person('administration')
        foreign = EditorialGroup.objects.create(name='Outro', slug='member-other')
        Membership.objects.create(user=actor, group=self.group, role='columnist')
        Membership.objects.create(user=self.founder, group=foreign, role='coordinator')
        self.assertEqual(list(managed_groups(actor)), [self.group])
        self.assertFalse(is_application_admin(actor))
        self.assertTrue(can_manage(actor))
        self.client.force_authenticate(actor)
        self.assertEqual(self.client.get('/api/auth/me').json()['profile_role_label'], 'Administração')
        self.assertEqual(self.client.get('/api/management/users').status_code, 403)

    def test_clergy_have_facilitator_permissions_and_revocable_delegation(self):
        for role in ['priest', 'deacon']:
            actor = self.person(role)
            Membership.objects.create(user=actor, group=self.group, role='columnist')
            self.assertEqual(list(author_groups(actor)), [self.group])
            self.assertFalse(managed_groups(actor).exists())
            self.assertTrue(facilitator_users().filter(pk=actor.pk).exists())
            self.assertFalse(can_manage(actor))
            delegation = Delegation.objects.create(coordinator=self.founder, facilitator=actor, can_edit_agenda=True, can_edit_mural=False, can_edit_newsletter=False)
            self.assertTrue(can_manage(actor, 'events'))
            self.assertFalse(can_manage(actor, 'notices'))
            delegation.delete()
            self.assertFalse(can_manage(actor))
            self.assertEqual(profile_role(actor)[0], role)
            self.assertEqual(self.client.get(f'/api/profiles?role={role}').status_code, 200)

    def test_delete_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.founder)
        self.assertEqual(client.delete(f'/api/management/team/{self.developer.pk}').status_code, 403)
