# Business logics

from librarymanagement.models import (
    Book,
    Author,
)  # Import here to avoid circular imports
from django.db import transaction
from django.utils import timezone
from django.utils import timezone
from librarymanagement.models import Author
from librarymanagement.utils import BookUtils
from librarymanagement.models import Category


class BookServices:

    @staticmethod
    def create_book(form, user):
        """
        Create a Book instance from a BookForm.
        Handles M2M relations, metadata, and saves in a transaction.
        Automatically creates authors if they do not exist.
        """
        book_data = form.cleaned_data

        with transaction.atomic():
            # Ensure authors exist or create them with basic information
            author_objects = AuthorServices.get_or_create_authors_from_strings(
                book_data.get("authors", [])
            )

            # Create the book
            book = Book.objects.create(
                library=book_data["library"],
                title=book_data["title"],
                isbn=book_data["isbn"],
                publication_year=book_data.get("publication_year"),
                edition=book_data.get("edition"),
                language=book_data.get("language", "English"),
                pages=book_data.get("pages"),
                resource_type=book_data.get("resource_type", "physical"),
                total_copies=book_data.get("total_copies", 1),
                available_copies=book_data.get("total_copies", 1),
                description=book_data.get("description", ""),
                shelf_location=book_data.get("shelf_location", ""),
                accession_number=BookUtils.generate_accession_number(),
                created_by=user if user.is_authenticated else None,
            )

            book.categories.set(book_data.get("categories", []))
            book.authors.set(author_objects)

            if book_data.get("publisher"):
                book.publisher = book_data["publisher"]
                book.save()

        return book


class AuthorServices:

    @staticmethod
    def get_or_create_author(first_name, last_name):
        """Get or create a single author by first and last name"""
        author, _ = Author.objects.get_or_create(
            first_name=first_name,
            last_name=last_name,
            defaults={
                "bio": "",
                "nationality": "",
                "created_at": timezone.now(),
            },
        )
        return author

    @staticmethod
    def get_or_create_authors_from_strings(author_names):
        """
        Accepts a list of full name strings (e.g., ["John Doe", "Jane Smith"]).
        Splits into first_name / last_name and ensures each author exists.
        Returns a list of Author instances.
        """
        authors = []
        for full_name in author_names:
            first_name, *last_name = full_name.strip().split(" ", 1)
            last_name = last_name[0] if last_name else ""
            authors.append(AuthorServices.get_or_create_author(first_name, last_name))
        return authors


class CategoryServices:
    @staticmethod
    def get_or_create_category(name):
        """Get or create a category by name"""
        category, _ = Category.objects.get_or_create(name=name)
        return category

    @staticmethod
    def get_or_create_categories_from_strings(category_names):
        """
        Accepts a list of category name strings (e.g., ["Fiction", "Science"]).
        Ensures each category exists and returns a list of Category instances.
        """
        categories = []
        for name in category_names:
            category, _ = Category.objects.get_or_create(name=name.strip())
            categories.append(category)
        return categories
