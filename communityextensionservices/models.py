from django.db import models

# Create your models here.
class Service(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        permissions = [
            ("access_community_extension_services_system", "Can access Community Extension Services system"),
        ]

    def __str__(self):
        return self.name