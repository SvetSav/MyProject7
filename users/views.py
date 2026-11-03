from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.types import OpenApiTypes
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
    PaymentCreateSerializer,
)
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)
from rest_framework import serializers

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from rest_framework import serializers as drf_serializers
from lms.models import Course
from lms.stripe_service import (
    create_stripe_product,
    create_stripe_price,
    create_stripe_checkout_session,
    retrieve_stripe_session,
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action == "retrieve":
            # чужой профиль → публичный сериализатор
            pk = self.kwargs.get('pk')
            if pk is not None and str(self.request.user.pk) == str(pk):
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


@extend_schema_view(
    list=extend_schema(
        summary='Список платежей',
        description=(
            'Возвращает пагинированный список платежей. '
            'Поддерживает сортировку по дате и фильтрацию по курсу, уроку и способу оплаты.'
        ),
        parameters=[
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Сортировка по дате оплаты: `payment_date` (по возрастанию) '
                            'или `-payment_date` (по убыванию).',
                enum=['payment_date', '-payment_date'],
            ),
            OpenApiParameter(
                name='course',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Фильтр по ID оплаченного курса.',
            ),
            OpenApiParameter(
                name='lesson',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Фильтр по ID оплаченного урока.',
            ),
            OpenApiParameter(
                name='payment_method',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по способу оплаты.',
                enum=['cash', 'transfer'],
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Номер страницы.',
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Количество элементов на странице (макс. 50).',
            ),
        ],
        responses={
            200: PaymentSerializer(many=True),
            401: OpenApiResponse(description='Требуется авторизация (JWT).'),
        },
        tags=['Платежи'],
    ),
    retrieve=extend_schema(
        summary='Получить платёж',
        description='Возвращает детальную информацию о платеже по его ID.',
        responses={
            200: PaymentSerializer,
            404: OpenApiResponse(description='Платёж не найден.'),
        },
        tags=['Платежи'],
    ),
    create=extend_schema(
        summary='Создать платёж',
        description=(
            'Создаёт запись о платеже. **Внимание:** этот эндпоинт создаёт платёж напрямую, '
            'без интеграции со Stripe. Для оплаты через Stripe используйте `POST /api/payments/create/`.'
        ),
        request=PaymentSerializer,
        responses={
            201: PaymentSerializer,
            400: OpenApiResponse(description='Некорректные данные.'),
        },
        tags=['Платежи'],
    ),
    update=extend_schema(
        summary='Обновить платёж (полностью)',
        request=PaymentSerializer,
        responses={
            200: PaymentSerializer,
            400: OpenApiResponse(description='Некорректные данные.'),
            404: OpenApiResponse(description='Платёж не найден.'),
        },
        tags=['Платежи'],
    ),
    partial_update=extend_schema(
        summary='Частично обновить платёж',
        request=PaymentSerializer,
        responses={
            200: PaymentSerializer,
            400: OpenApiResponse(description='Некорректные данные.'),
            404: OpenApiResponse(description='Платёж не найден.'),
        },
        tags=['Платежи'],
    ),
    destroy=extend_schema(
        summary='Удалить платёж',
        responses={
            204: OpenApiResponse(description='Платёж удалён.'),
            404: OpenApiResponse(description='Платёж не найден.'),
        },
        tags=['Платежи'],
    ),
)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ["payment_date"]
    ordering = ["-payment_date"]


class PaymentCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary='Создать платёж через Stripe',
        description=(
            'Создаёт продукт, цену и Checkout Session в Stripe. '
            'Сохраняет все ID и ссылку на оплату в модели Payment. '
            'Возвращает данные платежа и ссылку на оплату.'
        ),
        request=PaymentCreateSerializer,
        responses={
            201: OpenApiResponse(
                description='Платёж создан, ссылка на оплату возвращена.',
                response=inline_serializer(
                    name='PaymentCreateResponse',
                    fields={
                        'payment': PaymentSerializer(),
                        'payment_url': drf_serializers.URLField(),
                    },
                ),
            ),
            400: OpenApiResponse(description='Некорректные данные (например, курс не найден).'),
            401: OpenApiResponse(description='Требуется авторизация (JWT).'),
            502: OpenApiResponse(description='Ошибка Stripe (продукт/цена/сессия не созданы).'),
        },
        examples=[
            OpenApiExample(
                'Пример запроса',
                request_only=True,
                value={'course_id': 1, 'amount': 1500, 'payment_method': 'transfer'},
            ),
        ],
        tags=['Платежи'],
    )
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        course = get_object_or_404(Course, id=serializer.validated_data['course_id'])
        amount_rub = serializer.validated_data['amount']

        try:
            # 1. Продукт в Stripe
            product = create_stripe_product(
                name=course.title,
                description=course.description or '',
            )

            # 2. Цена (в копейках!)
            price = create_stripe_price(
                product_id=product['id'],
                amount=int(amount_rub * 100),
                currency='rub',   # если rub не проходит — замените на 'usd'
            )

            # 3. Checkout Session
            session = create_stripe_checkout_session(
                price_id=price['id'],
                success_url='http://127.0.0.1:8000/api/payments/success/',
                cancel_url='http://127.0.0.1:8000/api/payments/cancel/',
                metadata={
                    'user_id': request.user.id,
                    'course_id': course.id,
                },
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 4. Сохраняем платёж
        payment = Payment.objects.create(
            user=request.user,
            paid_course=course,
            amount=amount_rub,
            payment_method=serializer.validated_data['payment_method'],
            stripe_product_id=product['id'],
            stripe_price_id=price['id'],
            stripe_session_id=session['session_id'],
            payment_link=session['url'],
            payment_status=session['payment_status'],
        )

        return Response(
            {
                'payment': PaymentSerializer(payment).data,
                'payment_url': session['url'],
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentStatusAPIView(APIView):
    """Доп. задание: проверка статуса сессии Stripe."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary='Проверить статус платежа в Stripe',
        description='Запрашивает статус сессии у Stripe и синхронизирует его с моделью Payment.',
        parameters=[
            OpenApiParameter(
                name='session_id', type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='ID сессии Stripe (cs_test_...)',
            ),
        ],
        responses={
            200: inline_serializer(
                name='PaymentStatusResponse',
                fields={
                    'session_id': drf_serializers.CharField(),
                    'payment_status': drf_serializers.CharField(),
                    'amount_total': drf_serializers.IntegerField(),
                    'currency': drf_serializers.CharField(),
                },
            ),
            404: OpenApiResponse(description='Платёж с такой сессией не найден в нашей БД.'),
            502: OpenApiResponse(description='Ошибка Stripe.'),
        },
        tags=['Платежи'],
    )
    def get(self, request, session_id):
        if not Payment.objects.filter(stripe_session_id=session_id).exists():
            return Response(
                {'error': 'Платёж с таким session_id не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            data = retrieve_stripe_session(session_id)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        Payment.objects.filter(stripe_session_id=session_id).update(
            payment_status=data['payment_status'],
        )
        return Response(data)
