from django.db import models

# Create your models here.
class Performance(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        permissions = [
            ("access_performance_evaluation_system", "Can access Performance Evaluation system"),
        ]

    def __str__(self):
        return self.name