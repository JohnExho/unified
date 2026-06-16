# Django Management Commands

This document provides a comprehensive reference for all custom Django management commands available across the Unified Management System.

---

## Table of Contents

1. [Core Commands](#core-commands)
2. [Library Management](#library-management)
3. [Information Management](#information-management)
4. [Inventory Management](#inventory-management)
5. [Performance Evaluation](#performance-evaluation)
6. [Community Extension Services](#community-extension-services)
7. [Project Management](#project-management)

---

## Core Commands

### `seed_all`

**Description:** Runs all seeders across all 6 systems in one go.

**Usage:**
```bash
python manage.py seed_all
```

**What it does:**
- Seeds Community Extension Services (CES)
- Seeds Information Management
- Seeds Inventory Management
- Seeds Library Management
- Seeds Performance Evaluation
- Seeds Project Management

**Note:** This is a convenience command that calls all individual seeders sequentially. It continues even if one seeder fails.

---

## Library Management

### `seed_librarymanagement`

**Description:** Seeds Library Management with demo data including libraries, books, authors, publishers, categories, and borrowing transactions.

**Usage:**
```bash
python manage.py seed_librarymanagement
```

**Creates sample data for:**
- Libraries and locations
- Book catalog (authors, publishers, categories)
- Borrowing transactions
- User activity logs
- Reservation records

---

### `update_library_analytics`

**Description:** Updates library analytics including trending books, user clusters, and personalized recommendations.

**Usage:**
```bash
python manage.py update_library_analytics [OPTIONS]
```

**Options:**
- `--recommendations` - Update user recommendations only
- `--trending` - Update trending books only
- `--clusters` - Analyze and update user clusters only

**Example:**
```bash
python manage.py update_library_analytics --recommendations --trending
```

**Periodic execution:** Run this command regularly (daily or weekly) via cron or task scheduler to maintain fresh analytics.

---

### `train_library_random_forest`

**Description:** Trains a Random Forest model to classify high-demand books and predict demand patterns.

**Usage:**
```bash
python manage.py train_library_random_forest [OPTIONS]
```

**Options:**
- `--days INT` - Historical window (in days) for training features (default: 90)
- `--show-top INT` - Number of top predictions to display (default: 10)

**Example:**
```bash
python manage.py train_library_random_forest --days 120 --show-top 10
```

**Use case:** Identify high-demand books to inform purchasing and stocking decisions.

---

### `expire_reservations`

**Description:** Checks and expires old/stale book reservations that have passed their hold period.

**Usage:**
```bash
python manage.py expire_reservations
```

**What it does:**
- Identifies reservations that have exceeded their hold period
- Updates their status to expired
- Frees up books for other users

**Recommended frequency:** Daily (via cron job)

---

### `update_overdue_transactions`

**Description:** Checks and updates transactions where borrowed items are overdue.

**Usage:**
```bash
python manage.py update_overdue_transactions
```

**What it does:**
- Identifies borrowing transactions past their due date
- Updates transaction status to overdue
- Prepares data for overdue notifications

**Recommended frequency:** Daily (via cron job)

---

### `send_library_notifications`

**Description:** Sends automated notifications to users regarding due dates, overdue items, and reservations.

**Usage:**
```bash
python manage.py send_library_notifications [OPTIONS]
```

**Options:**
- `--dry-run` - Run without actually sending notifications (for testing)

**Example:**
```bash
python manage.py send_library_notifications --dry-run
```

**What it sends:**
- Due date reminders (items due soon)
- Overdue notifications (items past due)
- Reservation ready notifications

**Recommended frequency:** Daily (via cron job)

---

### `send_overdue_notifications`

**Description:** Sends notifications to users for overdue borrowing transactions.

**Usage:**
```bash
python manage.py send_overdue_notifications
```

**What it does:**
- Queries all overdue transactions
- Sends notifications to users with overdue items
- Logs notification delivery

**Recommended frequency:** Daily or multiple times per day

---

### `send_due_soon_notifications`

**Description:** Sends notifications to users for items that are due soon (within a configurable period).

**Usage:**
```bash
python manage.py send_due_soon_notifications
```

**What it does:**
- Identifies items due within the next 1-3 days (configurable)
- Sends reminders to borrowers
- Helps prevent overdue items

**Recommended frequency:** Daily

---

### `update_trending_books`

**Description:** Updates trending book metrics based on borrowing patterns.

**Usage:**
```bash
python manage.py update_trending_books [OPTIONS]
```

**Options:**
- `--period {daily|weekly|monthly|yearly}` - Period type for trending analysis (default: weekly)

**Example:**
```bash
python manage.py update_trending_books --period monthly
```

**What it does:**
- Analyzes borrowing statistics
- Identifies most-borrowed books
- Updates trending book records
- Useful for recommendations and collection development

---

### `cleanup_old_activities`

**Description:** Cleans up old user activity logs to maintain database performance.

**Usage:**
```bash
python manage.py cleanup_old_activities [OPTIONS]
```

**Options:**
- `--days INT` - Delete activities older than this many days (default: 90)

**Example:**
```bash
python manage.py cleanup_old_activities --days 180
```

**What it does:**
- Deletes old user activity records
- Helps manage database size
- Retains important historical data

**Recommended frequency:** Monthly or as needed

---

## Information Management

### `seed_informationmanagement`

**Description:** Seeds Information Management system with sample projects, beneficiary groups, partners, activities, and reports (23 items total).

**Usage:**
```bash
python manage.py seed_informationmanagement
```

**Creates sample data for:**
- Projects
- Beneficiary groups
- Partners and collaborations
- Activities and outputs
- Reports and templates
- ML models, pipelines, and experiments

---

### `train_information_naive_bayes`

**Description:** Trains a Naive Bayes classifier for IMS project classification and generates predictions.

**Usage:**
```bash
python manage.py train_information_naive_bayes [OPTIONS]
```

**Options:**
- `--days INT` - Lookback window (in days) for training data (default: 3650 = 10 years)
- `--show-top INT` - Number of top predictions to display (default: 10)

**Example:**
```bash
python manage.py train_information_naive_bayes --days 3650 --show-top 10
```

**Use case:** Automatically classify projects and predict project outcomes based on historical data.

---

## Inventory Management

### `seed_inventorymanagement`

**Description:** Seeds Inventory Management with sample categories, items, assets, and requisitions.

**Usage:**
```bash
python manage.py seed_inventorymanagement
```

**Creates sample data for:**
- Inventory categories and items
- Asset categories and assignments
- Asset maintenance records
- Requisitions and requisition items
- ML insights for inventory

**Seed User:** Automatically uses the first existing user or creates a seed user if needed.

---

## Performance Evaluation

### `seed_performanceevaluation`

**Description:** Seeds Performance Evaluation system with sample structure, scores, and recommendations.

**Usage:**
```bash
python manage.py seed_performanceevaluation
```

**Creates sample data for:**
- Academic terms and cycles
- Departments and user assignments
- Evaluation forms and criteria
- Evaluation scores and results
- Recommendations based on evaluations
- Rubrics and categories

---

## Community Extension Services

### `seed_ces`

**Description:** Seeds Community Extension Services with sample members, activities, services, and contributions.

**Usage:**
```bash
python manage.py seed_ces
```

**Creates sample data for:**
- Services and programs
- Members and membership history
- Activities and attendance
- Contributions and dues payments
- Document records
- ML insights for member engagement

---

### `train_ces_kmeans`

**Description:** Trains a K-Means clustering model to segment CES members into groups.

**Usage:**
```bash
python manage.py train_ces_kmeans [OPTIONS]
```

**Options:**
- `--k INT` - Number of clusters (default: 3)
- `--show-top INT` - Number of member rows to display (default: 10)

**Example:**
```bash
python manage.py train_ces_kmeans --k 4 --show-top 10
```

**Use case:** Segment members by engagement level, activity type, or contribution patterns for targeted outreach.

---

## Project Management

### `seed_projectmanagement`

**Description:** Seeds Project Management with sample teams, projects, tasks, and calendar events.

**Usage:**
```bash
python manage.py seed_projectmanagement
```

**Creates sample data for:**
- Teams and team members
- Projects and milestones
- Tasks and subtasks
- Calendar events
- Notifications
- ML insights for project planning

**Seed User:** Automatically uses the first existing user or creates a seed user if needed.

---

## Running Commands

### Basic Syntax

```bash
python manage.py <command_name> [OPTIONS]
```

### Within Python Shell

```python
from django.core.management import call_command

call_command('command_name', arg1='value1', arg2='value2')
```

### Scheduling with Cron

Example: Run library notifications daily at 9 AM

```bash
0 9 * * * /path/to/virtualenv/bin/python /path/to/manage.py send_library_notifications
```

Example: Run cleanup weekly

```bash
0 2 * * 0 /path/to/virtualenv/bin/python /path/to/manage.py cleanup_old_activities --days 180
```

### Django Q or Celery Integration

For more complex scheduling, integrate with Django Q or Celery:

```python
# Schedule periodic tasks
schedule, created = Schedule.objects.get_or_create(
    name='Send Library Notifications',
    defaults={
        'func': 'django.core.management.call_command',
        'args': "'send_library_notifications'",
        'schedule_type': Schedule.DAILY,
        'repeats': -1,
    }
)
```

---

## Best Practices

1. **Test with `--dry-run`**: For notification commands, use `--dry-run` first to see what would happen.

2. **Monitor Output**: Check command output for errors or unexpected behavior.

3. **Use Appropriate Periods**: 
   - Daily: Notifications, overdue checks, expiration checks
   - Weekly: Analytics updates, trending analysis
   - Monthly: Data cleanup, archival

4. **Database Backups**: Run cleanup commands during off-peak hours with backups in place.

5. **Gradual Rollout**: When running commands on large datasets, start with smaller date ranges.

6. **Logging**: Capture output by redirecting to log files:
   ```bash
   python manage.py command_name >> logs/command_name.log 2>&1
   ```

7. **Error Handling**: The `seed_all` command continues if one seeder fails, but check logs for failures.

---

## Troubleshooting

### Command not found
- Ensure the app is added to `INSTALLED_APPS` in settings
- Check that the command file is in `app/management/commands/` directory

### Permission errors
- Ensure proper database permissions
- Run as the appropriate user (web server user for production)

### Import errors
- Verify all dependencies are installed
- Check `requirements.txt` is up to date

### Slow performance
- Use `--days` parameter to limit historical data for ML training commands
- Run cleanup commands to reduce database size
- Consider running during off-peak hours

---

## Additional Resources

- [Django Management Commands Documentation](https://docs.djangoproject.com/en/stable/howto/custom-management-commands/)
- [Django Tasks & Scheduling](https://docs.djangoproject.com/en/stable/topics/async/)
- App-specific documentation in respective `copilot-instructions.md` files

