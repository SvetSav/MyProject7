from urllib.parse import urlparse

from rest_framework import serializers

ALLOWED_DOMAINS = ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be")


class YouTubeOnlyValidator:
    """
    Класс-валидатор для поля сериализатора.
    Разрешает только ссылки на youtube.com и youtu.be.
    Использование: validators=[YouTubeOnlyValidator(field='video_link')] в Meta.
    """

    def __init__(self, field):
        self.field = field

    def __call__(self, attrs):
        value = attrs.get(self.field)
        if not value:
            return  # пустое значение допустимо

        parsed = urlparse(value)
        domain = parsed.netloc.lower().split(":")[0]  # убираем порт, если есть

        if domain not in ALLOWED_DOMAINS:
            raise serializers.ValidationError(
                {
                    self.field: (
                        f"Ссылка должна вести только на youtube.com. "
                        f'Домен «{domain or "пусто"}» не разрешён.'
                    )
                }
            )

    def __eq__(self, other):
        # нужно для корректного сравнения при миграциях DRF
        return isinstance(other, YouTubeOnlyValidator) and self.field == other.field

    def __hash__(self):
        return hash((self.__class__.__name__, self.field))
