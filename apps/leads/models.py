from django.db import models


class Lead(models.Model):
    """A signup or demo request captured from the public marketing site.

    Leads are not users. An admin reviews a lead and then provisions the real
    account through /api/auth/users/, so public traffic never touches the auth
    tables.
    """

    class Kind(models.TextChoices):
        SIGNUP = 'signup', 'Account request'
        DEMO = 'demo', 'Demo request'

    class Status(models.TextChoices):
        NEW = 'new', 'New'
        CONTACTED = 'contacted', 'Contacted'
        CONVERTED = 'converted', 'Converted'
        REJECTED = 'rejected', 'Rejected'

    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SIGNUP)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    business_name = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=150, blank=True)
    message = models.TextField(blank=True)

    # Where the lead came from, e.g. the landing-page section id.
    source = models.CharField(max_length=60, blank=True)

    # Captured server-side for abuse triage; never accepted from the client.
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    note = models.TextField(blank=True, help_text='Internal follow-up notes.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('status', '-created_at')),
            models.Index(fields=('kind', '-created_at')),
        ]

    def __str__(self):
        return f'{self.get_kind_display()} — {self.full_name} <{self.email}>'
