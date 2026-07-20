from rest_framework import serializers

from .models import Lead


class LeadCreateSerializer(serializers.ModelSerializer):
    """Public write serializer.

    Only the fields a visitor can legitimately supply are exposed; status,
    source metadata and the internal note stay server-side.
    """

    class Meta:
        model = Lead
        fields = (
            'id', 'kind', 'full_name', 'email', 'phone',
            'business_name', 'location', 'message', 'source',
        )
        read_only_fields = ('id',)
        extra_kwargs = {
            'full_name': {'required': True, 'allow_blank': False},
            'email': {'required': True, 'allow_blank': False},
        }

    def validate_full_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('Please enter your full name.')
        return value

    def validate_email(self, value):
        return value.strip().lower()

    def validate_message(self, value):
        # Cheap link-spam guard; a genuine enquiry rarely needs several URLs.
        if value.lower().count('http') > 2:
            raise serializers.ValidationError('Message contains too many links.')
        return value.strip()

    def validate(self, attrs):
        if attrs.get('kind') == Lead.Kind.DEMO and not (
            attrs.get('phone') or attrs.get('business_name')
        ):
            raise serializers.ValidationError({
                'phone': 'Add a phone number or business name so we can reach you.',
            })
        return attrs


class LeadSerializer(serializers.ModelSerializer):
    """Admin-side read/update serializer."""

    class Meta:
        model = Lead
        fields = '__all__'
        read_only_fields = (
            'id', 'kind', 'full_name', 'email', 'phone', 'business_name',
            'location', 'message', 'source', 'ip_address', 'user_agent',
            'created_at', 'updated_at',
        )
