from rest_framework import serializers
from core.models import User


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["nickname", "email", "image"]

        extra_kwargs = {
            "email": {"required": False},
            "nickname": {"required": False},
            "image": {"required": False},
        }

    def validate_image(self, value):
        if value is None:
            raise serializers.ValidationError("image field cannot be null")
        return value

    def update(self, instance, validated_data):
        if "image" in validated_data:
            instance.image = validated_data["image"]
        return super().update(instance, validated_data)


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["eth_address", "nickname", "email", "image", "date_joined"]
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Convert image field to full URL if it exists
        if representation.get('image') and instance.image:
            request = self.context.get('request')
            if request is not None:
                # Build absolute URI using the request's scheme and host
                representation['image'] = request.build_absolute_uri(instance.image.url)
            else:
                # Fallback to relative URL if request is not available
                representation['image'] = instance.image.url
        return representation
