import uuid


class BookUtils:

    @staticmethod
    def generate_accession_number():
        """Generate a unique accession number for a book"""
        return str(f"ACC-{uuid.uuid4().hex[:8].upper()}")
