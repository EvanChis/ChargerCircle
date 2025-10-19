from django.apps import AppConfig

# tells Django about this app: its name and default ID field type
class RoomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rooms'
