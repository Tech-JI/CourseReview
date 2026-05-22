from rest_framework.authentication import SessionAuthentication


class CSRFCheckSessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        super().enforce_csrf(request)

        return super().authenticate(request)
