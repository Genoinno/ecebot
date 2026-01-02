from .ui import (
    BookshelfDropdownView,
    BorrowingDropdownView,
    AgreementView,
    BorrowingForm,
)
from .book import Book
from .spotify import Spotify

API = "http://openlibrary.org/api/volumes/brief/json/"
BOOK_COLLECTIONS = ["9780241252086", "9781840228038", "9781401308773", "9780142414460", "9786020495422", "9786020476612", "9766020495422", "9781484746691"]
for isbn in BOOK_COLLECTIONS:
    API += f"isbn:{isbn}|"
API_URL = API[:-1]
MESSAGE_SPLASH = [
    "Wise choice fella!",
    'How original! sure.. sure... `(¬_¬")`',
    "One book coming right up! `◝(˶˃ ᵕ ˂˶) ◜♡`",
    "Sure thing pal! I hope you get a good read from this book `٩(^ᗜ^ )و ´-`",
]
EMOJIES = ["🌃", "🐷", "🕯️", "🪖", "📜", "📜", "🖐️"]