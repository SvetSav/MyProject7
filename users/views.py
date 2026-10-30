from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated

from .filters import PaymentFilter
from .models import Payment, User
from .permissions import IsOwnerOfProfile
from .serializers import (
    PaymentSerializer,
    UserCreateSerializer,
    UserPublicSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action == "retrieve":
            # чужой профиль → публичный сериализатор
            obj = self.get_object()
            if obj == self.request.user:
                return UserSerializer
            return UserPublicSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = [AllowAny]
        elif self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsOwnerOfProfile]
        else:  # list, retrieve
            self.permission_classes = [IsAuthenticated]
        return [permission() for permission in self.permission_classes]


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ["payment_date"]
    ordering = ["-payment_date"]
