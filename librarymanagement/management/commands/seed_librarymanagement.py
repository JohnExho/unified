from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from librarymanagement.models import (
    Author,
    Book,
    BorrowingTransaction,
    Category,
    Library,
    Publisher,
    Reservation,
    UserActivity,
)


class Command(BaseCommand):
    help = "Seed Library Management demo data for Random Forest demand forecasting."

    def handle(self, *args, **options):
        now = timezone.now()
        User = get_user_model()

        library, _ = Library.objects.get_or_create(
            name="Main Campus Library",
            defaults={
                "description": "Primary circulation and reference library.",
                "location": "Main Building",
                "contact_email": "library@example.com",
                "contact_phone": "09170000000",
            },
        )

        publisher, _ = Publisher.objects.get_or_create(
            name="Unified University Press",
            defaults={
                "website": "https://example.com",
                "email": "press@example.com",
            },
        )

        category_names = [
            "Education",
            "Technology",
            "Science",
            "Literature",
            "Business",
        ]
        categories = {
            name: Category.objects.get_or_create(name=name)[0]
            for name in category_names
        }

        author_specs = [
            ("Ana", "Ramos"),
            ("Luis", "Navarro"),
            ("Paula", "Santos"),
            ("Miguel", "Reyes"),
            ("Carla", "Mendoza"),
        ]
        authors = {}
        for first_name, last_name in author_specs:
            author, _ = Author.objects.get_or_create(
                first_name=first_name,
                last_name=last_name,
            )
            authors[f"{first_name} {last_name}"] = author

        library_admin = User.objects.get(username="LibraryAdmin")
        users = [library_admin]
                
        book_specs = [
            {
                "accession_number": "LIB-0001",
                "title": "Foundations of Community Learning",
                "author": "Ana Ramos",
                "category": "Education",
                "publication_year": 2021,
                "pages": 320,
                "resource_type": "physical",
                "total_copies": 4,
                "available_copies": 2,
                "status": "available",
            },
            {
                "accession_number": "LIB-0002",
                "title": "Practical Data Science for Schools",
                "author": "Luis Navarro",
                "category": "Technology",
                "publication_year": 2022,
                "pages": 410,
                "resource_type": "digital",
                "total_copies": 5,
                "available_copies": 3,
                "status": "available",
            },
            {
                "accession_number": "LIB-0003",
                "title": "Applied Research Methods",
                "author": "Paula Santos",
                "category": "Science",
                "publication_year": 2020,
                "pages": 360,
                "resource_type": "physical",
                "total_copies": 3,
                "available_copies": 1,
                "status": "available",
            },
            {
                "accession_number": "LIB-0004",
                "title": "Modern Philippine Literature",
                "author": "Miguel Reyes",
                "category": "Literature",
                "publication_year": 2019,
                "pages": 280,
                "resource_type": "physical",
                "total_copies": 2,
                "available_copies": 2,
                "status": "available",
            },
            {
                "accession_number": "LIB-0005",
                "title": "Entrepreneurship in Practice",
                "author": "Carla Mendoza",
                "category": "Business",
                "publication_year": 2023,
                "pages": 250,
                "resource_type": "physical",
                "total_copies": 3,
                "available_copies": 3,
                "status": "available",
            },
            {
                "accession_number": "LIB-0006",
                "title": "Intro to Environmental Systems",
                "author": "Ana Ramos",
                "category": "Science",
                "publication_year": 2018,
                "pages": 295,
                "resource_type": "physical",
                "total_copies": 2,
                "available_copies": 2,
                "status": "available",
            },
            {
                "accession_number": "LIB-0007",
                "title": "Digital Citizenship Handbook",
                "author": "Luis Navarro",
                "category": "Education",
                "publication_year": 2024,
                "pages": 210,
                "resource_type": "digital",
                "total_copies": 6,
                "available_copies": 6,
                "status": "available",
            },
            {
                "accession_number": "LIB-0008",
                "title": "Public Service Innovation",
                "author": "Paula Santos",
                "category": "Business",
                "publication_year": 2021,
                "pages": 330,
                "resource_type": "physical",
                "total_copies": 3,
                "available_copies": 3,
                "status": "available",
            },
        ]

        books = []
        created_books = 0
        for spec in book_specs:
            book, created = Book.objects.update_or_create(
                accession_number=spec["accession_number"],
                defaults={
                    "library": library,
                    "title": spec["title"],
                    "publisher": publisher,
                    "publication_year": spec["publication_year"],
                    "pages": spec["pages"],
                    "resource_type": spec["resource_type"],
                    "total_copies": spec["total_copies"],
                    "available_copies": spec["available_copies"],
                    "status": spec["status"],
                    "language": "English",
                    "created_by": library_admin,
                },
            )
            book.authors.set([authors[spec["author"]]])
            book.categories.set([categories[spec["category"]]])
            books.append(book)
            if created:
                created_books += 1

        marker = "seed_librarymanagement"
        BorrowingTransaction.objects.filter(book__in=books, notes=marker).delete()
        Reservation.objects.filter(book__in=books, notes=marker).delete()
        UserActivity.objects.filter(book__in=books, session_id=marker).delete()

        high_demand_accessions = {"LIB-0001", "LIB-0002", "LIB-0003"}
        books_by_accession = {book.accession_number: book for book in books}

        borrowed_created = 0
        reservations_created = 0
        views_created = 0

        for accession in high_demand_accessions:
            book = books_by_accession[accession]

            for i in range(3):
                BorrowingTransaction.objects.create(
                    user=library_admin,
                    book=book,
                    due_date=now + timedelta(days=14),
                    status="active",
                    notes=marker,
                    issued_by=library_admin,
                )
                borrowed_created += 1

            for i in range(2):
                Reservation.objects.create(
                    user=library_admin,
                    book=book,
                    expiry_date=now + timedelta(days=3),
                    status="pending",
                    notes=marker,
                )
                reservations_created += 1

            for i in range(6):
                UserActivity.objects.create(
                    user=library_admin,
                    book=book,
                    activity_type="view",
                    session_id=marker,
                    metadata={"seed": True},
                )
                views_created += 1

        for accession in set(books_by_accession.keys()) - high_demand_accessions:
            book = books_by_accession[accession]
            UserActivity.objects.create(
                user=library_admin,
                book=book,
                activity_type="view",
                session_id=marker,
                metadata={"seed": True},
            )
            views_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Library Management demo data seeded/updated. "
                f"created_books={created_books} total_books={Book.objects.count()} "
                f"seed_borrows={borrowed_created} seed_reservations={reservations_created} seed_views={views_created}"
            )
        )
