from rest_framework.generics import (CreateAPIView,
                                     RetrieveUpdateDestroyAPIView, ListAPIView, ListCreateAPIView)
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .. import serializers, models
from ..models import User, Notification
from ..permissions import IsOwner, IsRelatedToThatUser
from ..serializers import NotificationSerializer, UserSerializer


class RegisterView(CreateAPIView):
    serializer_class = serializers.RegistrationSerializer
    permission_classes = (AllowAny,)

    def perform_create(self, serializer):
        try:
            User.objects.get(username=serializer.validated_data["username"])
            return Response({"error": "user already exists"}, 400)
        except:
            super().perform_create(serializer)


class ProfileView(RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.UserSerializer

    def get_object(self):
        return self.request.user


class LoginView(TokenObtainPairView):
    serializer_class = serializers.CustomTokenObtainPairSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        access_token = serializer.validated_data['access']
        user = serializer.validated_data['user']

        models.IssuedToken.objects.create(user=user, token=access_token)

        return Response(
            {'token': access_token},
            status=status.HTTP_200_OK
        )


class NotificationsListView(ListCreateAPIView):
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()

    def create(self, request, *args, **kwargs):     
        request.data["user"] = request.user.id
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class MarkNotificationsReadView(APIView):
    parser_classes = (JSONParser,)
    permission_classes = (IsRelatedToThatUser, IsAuthenticated)

    def post(self, request):
        if not isinstance(request.data.get("ids"), list):
            return Response({"error": "bad request"}, 400)
        for n_id in request.data["ids"]:
            notification = Notification.objects.get(id=n_id)
            notification.is_read = True
            notification.save()
        return Response({"status": "ok"}, 200)


class UserListView(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        return super().get_queryset().exclude(id=self.request.user.id)
