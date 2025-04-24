from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model() # Get the active user model (default or custom)

class CurrentUserSerializer(serializers.ModelSerializer):
    """
    Serializer for the /auth/user/ endpoint provided by dj-rest-auth.
    """
    class Meta:
        model = User
        # Define the fields you want to expose about the logged-in user
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = fields # User details are read-only via this endpoint