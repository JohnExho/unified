def percent_change(current, previous):
    if previous == 0:
        return 0
    return round(((current - previous) / previous) * 100, 1)
