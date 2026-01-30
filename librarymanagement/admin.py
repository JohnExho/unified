from django.contrib import admin
from .models import (
	Library,
	Category,
	Author,
	Publisher,
	Book,
	BorrowingTransaction,
	Reservation,
	UserActivity,
	BookRecommendation,
	TrendingBook,
	UserCluster,
	LibraryReport,
	Notification,
)

admin.site.register(Library)
admin.site.register(Category)
admin.site.register(Author)
admin.site.register(Publisher)
admin.site.register(Book)
admin.site.register(BorrowingTransaction)
admin.site.register(Reservation)
admin.site.register(UserActivity)
admin.site.register(BookRecommendation)
admin.site.register(TrendingBook)
admin.site.register(UserCluster)
admin.site.register(LibraryReport)
admin.site.register(Notification)

