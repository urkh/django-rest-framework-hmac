import json
import pytest

from pretend import stub

from django.test import TestCase, override_settings
from django.conf.urls import include, url
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_hmac import HMACAuthentication, HMACSigner

factory = APIRequestFactory()

class BasicView(APIView):
    authentication_classes = (HMACAuthentication,)

    def post(self, request, *args, **kwargs):
        return Response(data=request.data)


# urlpatterns = [
#     url(r'^auth/$', BasicView.as_view()),
# ]

class HMACAuthenticationUnitTests(TestCase):

    def test_get_user(self):
        user = User.objects.create_user('bob')
        request = stub(META={'Key': user.hmac_key.key})

        ret = HMACAuthentication().get_user(request)

        assert ret == user

    def test_get_user__fail_if_key_not_sent(self):
        request = stub(META={})

        with pytest.raises(AuthenticationFailed):
            HMACAuthentication().get_user(request)

    def test_get_user__fail_if_invalid_key(self):
        request = stub(META={'Key': 'invalid'})

        with pytest.raises(AuthenticationFailed):
            HMACAuthentication().get_user(request)

    def test_get_signature(self):
        signature = b'my-signature'
        request = stub(META={'Signature': signature})

        ret = HMACAuthentication().get_signature(request)

        assert ret == signature

    def test_get_signature__fail_if_key_not_sent(self):
        request = stub(META={})

        with pytest.raises(AuthenticationFailed):
            HMACAuthentication().get_signature(request)

    def test_get_signature__fail_if_not_bytes(self):
        signature = 'str'
        request = stub(META={'Signature': signature})

        with pytest.raises(AuthenticationFailed):
            HMACAuthentication().get_signature(request)


class HMACAuthenticationIntegrationTests(APITestCase):

    def setUp(self):
        self.post_data = {'foo': 'bar'}
        self.fake_request = stub(data=self.post_data)
        self.user = User.objects.create_user('bob')
        self.view = BasicView.as_view()

    def test_post_200(self):
        signature, _ = HMACSigner(self.user.hmac_key.secret).calc_signature(self.fake_request)

        request = factory.post(
            '/', self.post_data, format='json', **{'Key': self.user.hmac_key.key, 'Signature': signature})
        response = self.view(request)

        assert response.status_code == status.HTTP_200_OK

    def test_post_400__invalid_signature(self):
        request = factory.post(
            '/', self.post_data, format='json', **{'Key': self.user.hmac_key.key, 'Signature': b'invalid'})
        response = self.view(request)

        assert response.status_code == status.HTTP_403_FORBIDDEN