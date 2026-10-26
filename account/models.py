from django.contrib.auth.models import AbstractUser


# Create your models here.
class User(AbstractUser):
    # On garde le champ username (Django l'exige pour AbstractUser)
    # mais on ne l'utilisera pas pour la connexion.
    # On peut le rendre optionnel dans les formulaires.
    pass
