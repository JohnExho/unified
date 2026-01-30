from django import forms
from .models import Book

import json
from .models import Category


class BookForm(forms.ModelForm):
    categories_tagify = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Book
        fields = [
            "library",
            "title",
            "isbn",
            "publication_year",
            "edition",
            "language",
            "pages",
            "resource_type",
            "total_copies",
            "description",
            "shelf_location",
            "authors",
            "publisher",
            # 'categories' will be set in clean() from categories_tagify
        ]

    def clean(self):
        cleaned_data = super().clean()
        tagify_raw = self.data.get("categories") or self.data.get("categories_tagify")
        category_names = []
        if tagify_raw:
            try:
                tagify_data = json.loads(tagify_raw)
                if isinstance(tagify_data, list):
                    category_names = [
                        item["value"] for item in tagify_data if "value" in item
                    ]
            except Exception:
                # fallback: comma-separated
                category_names = [x.strip() for x in tagify_raw.split(",") if x.strip()]
        cleaned_data["categories"] = category_names
        return cleaned_data
