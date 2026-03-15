1. Library Settings Management
   Missing Model: LibrarySettings model doesn't exist

Need to store:
Library name, default loan period, maximum renewals
Maximum books per user
Fine settings (enable fines, daily fine amount, maximum fine, grace period)
Notification preferences (email/SMS for due dates, overdue notices, reservation alerts)
Feature toggles (book recommendations, trending analysis, user analytics)
Missing Functions:

save_library_settings() - Save general library configuration
update_fine_settings() - Update fine and fee configuration
toggle_notification_settings() - Enable/disable notification types
toggle_feature_settings() - Enable/disable system features
export_library_data() - Export library data
backup_library_database() - Create database backup
restore_library_backup() - Restore from backup
clear_analytics_data() - Clear user analytics and activity logs 2. Book Management - Missing CRUD Operations
Missing Functions:

edit_book() - Update book information (no edit view exists)
delete_book() - Remove book from system
toggle_book_status() - Change book status (available/maintenance/lost/damaged)
upload_cover_image() - Upload book cover
upload_digital_file() - Upload digital book file (for digital resources)
bulk_import_books() - Import books from CSV/Excel
export_books() - Export book list 3. Author & Publisher Management
Missing Functions:

edit_author() - Update author information
delete_author() - Remove author
toggle_author_status() - Activate/deactivate author
edit_publisher() - Update publisher information
delete_publisher() - Remove publisher
toggle_publisher_status() - Activate/deactivate publisher 4. Category Management
Missing entirely - No category CRUD operations exist:

list_categories() - Display categories
add_category() - Create new category
edit_category() - Update category
delete_category() - Remove category 5. Transaction Management
Missing Functions:

edit_transaction() - Modify transaction details
mark_book_lost() - Mark transaction/book as lost
waive_fine() - Waive or reduce fine amount
pay_fine() - Record fine payment
extend_due_date() - Manually extend due date
bulk_return_books() - Return multiple books at once 6. Reservation Management
Missing Functions:

create_reservation() - User creates reservation (only staff actions exist)
edit_reservation() - Modify reservation
extend_reservation_expiry() - Extend pickup deadline 7. User Activity Tracking
Missing Functions:

track_book_view() - Log when user views book details
track_search() - Log search queries
export_activity_log() - Export activity data
filter_activities() - Filter by user/book/type/date
delete_old_activities() - Clean up old activity logs 8. Recommendations System
Missing Functions:

generate_recommendations() - Create personalized recommendations
refresh_recommendations() - Regenerate recommendations for user
dismiss_recommendation() - Remove recommendation
mark_recommendation_viewed() - Track when user sees recommendation 9. Trending/Popular Books
Missing Functions:

update_trending_metrics() - Calculate trending scores (should be scheduled job)
get_trending_by_category() - Filter trending books by category
export_trending_report() - Export trending data 10. Reports & Analytics
Missing Functions:

download_report() - Download generated report as PDF/Excel
delete_report() - Remove old reports
schedule_report() - Schedule automatic report generation
get_report_details() - View full report details 11. User Profile & Settings (user-settings page)
Partially implemented, missing:

upload_profile_picture() - Avatar upload (exists in code but may need testing)
update_notification_preferences() - User notification settings
view_borrowing_history() - User's complete borrowing history
view_reservation_history() - User's reservation history
export_user_data() - Export user's library data (GDPR)
delete_account() - Account deletion request 12. Notification System
Missing Functions:

send_due_soon_notifications() - Scheduled task to notify users
send_overdue_notifications() - Notify about overdue books
send_reservation_ready_notification() - Already exists but may need testing
send_reservation_expiring_notification() - Warn about expiring reservations
mark_notification_read() - Mark as read
delete_notification() - Remove notification
get_unread_count() - Count unread notifications 13. Search & Filter
Missing Functions:

advanced_book_search() - Search by multiple criteria
filter_books() - Filter by category/author/publisher/status
filter_transactions() - Filter by date/status/user
filter_reservations() - Filter by status/date 14. Data Mining & Clustering
Models exist but no implementation:

cluster_users() - Group users by behavior patterns
update_user_clusters() - Refresh clustering
get_cluster_characteristics() - Analyze cluster patterns
recommend_acquisitions() - Suggest books to purchase 15. API Endpoints (if needed)
Missing REST API for:

Book CRUD operations
Transaction operations
Search functionality
User profile management 16. Scheduled Tasks/Management Commands
Missing scheduled jobs:

update_overdue_status() - Mark overdue transactions
expire_old_reservations() - Auto-expire reservations
send_daily_notifications() - Batch notifications
update_trending_books() - Recalculate trending
cleanup_old_data() - Archive/delete old records
generate_scheduled_reports() - Auto-generate reports 17. Permission & Access Control
Missing functions:

check_book_borrow_eligibility() - Verify user can borrow
check_user_limits() - Validate book limits
restrict_overdue_users() - Block users with overdue items
Priority Implementation Order
High Priority: Library settings, book edit/delete, category management
Medium Priority: Advanced search/filter, user history, notification system
Low Priority: Data mining, API endpoints, scheduled tasks

# Sytem - Requirements:

- the programming paradigm must strictly follow SOLID principles
- EG: services.py + (forms.py if forms) + utils.py -> views.py -> html page

## services.py

- contains business logic

## utils.py

- contains utility functions

## update the models as necessary

## RBAC

- look for the core app to reuse auth
- users can borrow books , renew, return, updated their profiles and access digital resources only only
- admin can do what user can do but , can add books, library, publishers , ability to record and lend physical books
- super admin can do what admin can do but can view the superadmin modules in the sidebar while the admin cannot and is restricted to its assigned system
- eg: test1234 user -> librarymanagement : can only access libarary management
- make uploading a book thumbnail optional (update the models if necessary)

## new

- if there are users strictly manage the user access to user level only, no sensitive mutations (like adding books etc...)
- use the login page from the core app however change the url for each system (eg: /core/login/ -> /librarymanagement/login/)

## test all the endpoints by mimicking the existing forms

- update the forms.py and the html forms if necessary inorder to match
