from rest_framework import serializers

from .models import Payment, User


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = (
            'id', 'user', 'payment_date',
            'stripe_product_id', 'stripe_price_id',
            'stripe_session_id', 'payment_link', 'payment_status',
        )

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class PaymentCreateSerializer(serializers.Serializer):
    course_id = serializers.IntegerField(help_text='ID оплачиваемого курса')
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=1,
        help_text='Сумма в рублях (минимум 1.00)',
    )
    payment_method = serializers.ChoiceField(
        choices=['cash', 'transfer'],
        default='transfer',
        help_text='Способ оплаты',
    )

    def validate_course_id(self, value):
        from lms.models import Course
        if not Course.objects.filter(id=value).exists():
            raise serializers.ValidationError('Курс с таким ID не найден.')
        return value

# Для регистрации
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "city",
            "avatar",
        )

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует"
            )
        return value.lower()

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# Для просмотра/редактирования своего профиля
class UserSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "city",
            "avatar",
            "payments",
        )
        read_only_fields = ("id", "email")


# Для просмотра чужого профиля (без last_name, payments, password)
class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "phone", "city", "avatar")
