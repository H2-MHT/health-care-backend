from users.models import User
from users.serializers import UserSerializer

def search(query, user_role, search_role):
    if not query or not search_role:
         return []

    role_permissions = {
        "Patient": ["Doctor", "Clinic"],
        "Doctor": ["Patient", "Clinic"],
        "Clinic": ["Doctor", "Patient"]
    }

    if search_role not in role_permissions.get(user_role, []):
         return []

    filters = User.objects.filter(role=search_role, first_name__istartswith=query) | \
              User.objects.filter(role=search_role, last_name__istartswith=query)

    return UserSerializer(filters, many=True).data
    