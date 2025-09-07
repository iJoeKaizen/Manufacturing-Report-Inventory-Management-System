def get_user_role(user):
    if hasattr(user, "role"):
        return user.role.upper() 
    
    if user.is_superuser:
        return "ADMIN"
    elif user.is_staff:
        return "MANAGER"
    else:
        return "OPERATOR"
