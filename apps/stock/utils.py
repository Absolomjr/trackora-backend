from django.utils import timezone


def generate_reference(prefix, model):
    """
    Build a human-friendly unique reference such as 'SIN-20260623-0007'.

    prefix: short code, e.g. 'SIN' (stock in) or 'SOUT' (stock out).
    model:  the model class to count today's records for sequencing.
    """
    today = timezone.now()
    date_part = today.strftime('%Y%m%d')
    count_today = model.objects.filter(created_at__date=today.date()).count() + 1
    return f'{prefix}-{date_part}-{count_today:04d}'
