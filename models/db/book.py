import json

from .db import Base
from models.book import Book
from sqlalchemy import Column, Integer, String, Text, JSON, select
from sqlalchemy.orm import relationship

class BookDB(Base):
    __tablename__ = 'books'
    isbn = Column(String(15), primary_key=True)

    identifiers = Column(JSON)        # {"Openlib": "...", "ISBN_13": "..."}

    available = Column(Integer)      

    url = Column(String(255))
    emoji = Column(String(10))        # stores an emoji character
    publish_date = Column(String(50))
    title = Column(String(255))
    description = Column(Text(300))
    cover = Column(String(255))

    # JSON arrays
    publishers = Column(JSON)         # ["Publisher A", "Publisher B"]
    authors = Column(JSON)            # ["Author A", "Author B"]

    borrow_records = relationship("BorrowingRecordDB", back_populates="book")

    @staticmethod
    async def add(session, emoji, json_payload):
        book = BookDB(
            isbn=json_payload["isbns"][0],
            identifiers=json.dumps(json_payload["data"]["identifiers"]),
            available=1,
            url=json_payload["data"]["url"],
            emoji=emoji,
            publish_date=json_payload["publishDates"][0],
            title=json_payload["data"]["title"],
            description=json_payload["details"]["details"]["description"]["value"],
            cover=json.dumps(json_payload["data"]["cover"]),
            publishers=json.dumps(json_payload["details"]["details"]["publishers"]),
            authors=json.dumps(json_payload["data"]["authors"])
        )
        
        session.add(book)   
        await session.commit()
    
    @staticmethod
    async def get_by_id(session, isbn, parse_to_book):
        book = (await session.execute(select(BookDB).where(BookDB.isbn == isbn))).scalar()
        if parse_to_book:
            return Book(book)
        return book
    
    @staticmethod
    async def get_allowed_books(session, parse_to_book):
        books = (await session.execute(select(BookDB).where(BookDB.available == 1))).scalars().all()
        if parse_to_book:
            return [Book(book) for book in books]
        return books
    
    @staticmethod
    async def get_all(session, parse_to_book):
        books = (await session.execute(select(BookDB))).scalars().all()
        if parse_to_book:
            return [Book(book) for book in books]
        return books

    @staticmethod
    async def borrow(session, isbn, reverse: bool = False):
        book: BookDB = await BookDB.get_by_id(session, isbn, False)

        if book:
            book.available = 0 + reverse
            await session.commit()
            return True
        return False