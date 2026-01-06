import discord
import datetime
import asyncio
import random
import json

from discord.ext import commands
from models.db import (
    BorrowingRecordDB, 
    BookDB, 
    BorrowingStatus,
    WarningDB,
    WarningType,
    AsyncSessionLocal, 
    engine, 
    Base
)
from models import (
    Book,
    BookshelfDropdownView,
    AgreementView,
    BorrowingDropdownView,
    BorrowingForm,
    MESSAGE_SPLASH,
)
from models import (
    Book,
    BookshelfDropdownView,
    AgreementView,
    BorrowingDropdownView,
    BorrowingForm,
    MESSAGE_SPLASH,
)
from utils import (
    TIMEFORMAT,
    EC_SERVER_ID,
    LIBRARIAN_ROLE,
    build_receipt_image,
    build_renewed_receipt_image,
    build_returned_receipt_image
)

class Library(commands.Cog):
    """This is a cog with Library commands:
    - Borrow
    - Renew
    - Return
    - Accept
    - Denied

    - View our curated book collection
    - Checkout our guidelines and rules

    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["lib", "perpustakaan", "perpus"])
    async def library(self, ctx: commands.Context):
        em = (
            discord.Embed(
                title="English Club Library",
                description="""Howdy Guyziee :wave: This is our shared book collections. 
            You can borrow our books by registering using the command :
            ```
            ec!borrow
            ```
            """,
                url="http://discord.com",
                color=discord.Color.blurple(),
            )
            .add_field(name="Not selected", value="Please select a book from the dropdown")
            .set_author(
                name="English Club Committee Board", icon_url="attachment://EC.jpeg"
            )
            .set_image(url="attachment://output.png")
        )

        async with AsyncSessionLocal() as session:
            books: Book = await BookDB.get_all(session, True)
            await ctx.send(
                file=discord.File("images/EC.jpeg"),
                embed=em,
                view=BookshelfDropdownView(em, books, ctx.author),
            )

    @commands.command(aliases=["bor", "minjem", "minjam"])
    @commands.cooldown(1, 60, commands.BucketType.default)
    async def borrow(self, ctx: commands.Context):
        has_role = self.patron_role in ctx.author.roles
        channel = self.bot.record_channel
        check_author = lambda inter: inter.user == ctx.author
        modal_check = (
            lambda inter: inter.type == discord.InteractionType.modal_submit
            and check_author(inter)
        )
        msg: discord.Message = None
        step = 1
        last_step = 3

        async with AsyncSessionLocal() as session:
            if (await BorrowingRecordDB.user_is_borrowing(session, ctx.author.id)):
                return await ctx.send("You can only borrow one book at a time!")
        
            allowed_books = await BookDB.get_allowed_books(session, True)

            if not has_role:
                with open("policy.txt", "rb") as f:
                    file = discord.File(f)

                msg: discord.Message = await ctx.send(
                    f"**`[{step}/{last_step}]`** Let's get started!\nOur policy helps to ensure qualities of our services to patrons. Please confirm our attached policy by pressing the green button bellow!",
                    file=file,
                    view=AgreementView(self, ctx.author),
                )
                step += 1
                await asyncio.sleep(1)

                inter: discord.Interaction = await self.bot.wait_for("interaction", check=check_author)
                if not (inter.data["id"] == 2):
                    return

                await inter.response.edit_message(
                    content=f"**`[{step}/{last_step}]`** Thanks for agreeing to our policy\nYou may choose one book of your liking through the dropdown bellow.",
                    attachments=[],
                    view=BorrowingDropdownView(msg, allowed_books, ctx.author),
                )
                step += 1

            else:
                last_step = 2
                msg = await ctx.send(
                    content=f"**`[{step}/{last_step}]`** Howdy Patron!\nYou may choose one book of your liking through the dropdown bellow.",
                    view=BorrowingDropdownView(msg, allowed_books, ctx.author),
                )
                step += 1

            inter: discord.Interaction = await self.bot.wait_for("interaction", check=check_author)
            selected_book_isbn = inter.data["values"][0]
            book = await BookDB.get_by_id(session, selected_book_isbn, True)
            
            await msg.edit(
                content=f"**`[{step}/{last_step}]`** `⸜(｡˃ ᵕ ˂ )⸝♡` Almost there!\nYou just need to enter information through this form.",
                attachments=[],
                view=None,
            )
            
            await inter.response.send_modal(BorrowingForm(timeout=120, selected_book=book))

            inter: discord.Interaction = await self.bot.wait_for("interaction", check=modal_check)
            name = inter.data["components"][0]["components"][0]["value"]
            phone_number = inter.data["components"][1]["components"][0]["value"]
            kelas = inter.data["components"][2]["components"][0]["value"]
            renewed_date = datetime.datetime.now() + datetime.timedelta(days=7)
            await inter.response.send_message(f"`( ╹ -╹)? Hmm?` *{book.title}*? " + random.choice(MESSAGE_SPLASH), ephemeral=True)

            latest_record = (await BorrowingRecordDB.get_latest(session))
            latest_record_id = (latest_record.id if latest_record else 0) + 1

            file = discord.File(
                build_receipt_image(
                    book, name, latest_record_id, renewed_date.strftime(TIMEFORMAT)
                ),
                "receipt.png",
            )

            em = (
                discord.Embed(
                    title=name,
                    description=f"**{ctx.author.mention}** has borrowed a book!\n\n{name} • {kelas} • {phone_number}",
                    color=discord.Color.yellow(),
                    timestamp=datetime.datetime.now(),
                )
                .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
                .set_footer(text="Borrowed")
                .set_image(url="attachment://receipt.png")
                .set_thumbnail(url=book.get_cover_url("large"))
            )

            await BookDB.borrow(session, book.isbn)
            await BorrowingRecordDB.create(
                session,
                int(self, ctx.author.id),
                book.isbn,
                f"{name}:{phone_number}:{kelas}"
            )

            message = await channel.send(self.bot.librarian_role.mention, embed=em, file=file)
            await msg.edit(
                content=f"**`[{step}/{last_step}, Pending]`** Done! `(,,> ᴗ <,,)`\nYour request is being validated by us.\n**We will notify you shortly via DM**"
            )

            await BorrowingRecordDB.add_message_id(session, latest_record_id, message.id)
        

    @commands.command(aliases=["acc", "ac"])
    @commands.has_role(LIBRARIAN_ROLE)
    @commands.cooldown(1, 60, commands.BucketType.default)
    async def accept(self, ctx: commands.Context, receipt_id: int):
        await ctx.send(f"Approving **{receipt_id}**? \n**(yes, no)**")
        msg = await self.bot.wait_for("message", check=lambda msg: msg.content.lower() in ["yes", "no"] and msg.channel == ctx.channel and msg.author == ctx.author)
        async with AsyncSessionLocal() as session:
            record = await BorrowingRecordDB.get_by_id(session, receipt_id)
            book = await BookDB.get_by_id(session, record.book_isbn, True)
            name, phone_number, _ = record.remarks.split(":")
            
            if not record or not record.status == BorrowingStatus.PENDING:
                return await ctx.send("Record does not exist or cannot be approved!")
            
            file = discord.File(
                build_receipt_image(
                    book, name, record.id, record.due_date.strftime(TIMEFORMAT)
                ),
                "receipt.png",
            )

            em = (
                discord.Embed(
                    title=name,
                    description=f"**{ctx.author.mention}** has borrowed a book!\n\n{name} • {phone_number}",
                    color=discord.Color.yellow(),
                    timestamp=datetime.datetime.now(),
                )
                .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
                .set_footer(text="Borrowed")
                .set_image(url="attachment://receipt.png")
                .set_thumbnail(url=book.get_cover_url("large"))
            )
            
            match msg.content:
                case "yes":
                    member = (self.bot.get_guild(EC_SERVER_ID).get_member(record.user_id))
                    await (await self.bot.record_channel.fetch_message(record.message_id)).add_reaction("✅")
                    await member.send(f"Hi! We have approved your request\n**Please come to Language Room (Ruang Bahasa) afterschool!**", embed=em, file=file)
                    await member.add_roles(self.patron_role)
                    await BorrowingRecordDB.approve_record_by_id(session, receipt_id)
                    return await ctx.send(f"Approved **{receipt_id}**!")
                case _:
                    return await ctx.send("Aborting...")
                
    @commands.command(aliases=["den"])
    @commands.has_role(LIBRARIAN_ROLE)
    @commands.cooldown(1, 60, commands.BucketType.default)
    async def denied(self, ctx: commands.Context, receipt_id: int):
        await ctx.send(f"Denying **{receipt_id}**? \n**(yes, no)**")
        msg = await self.bot.wait_for("message", check=lambda msg: msg.content.lower() in ["yes", "no"] and msg.channel == ctx.channel and msg.author == ctx.author)

        async with AsyncSessionLocal() as session:
            record = await BorrowingRecordDB.get_by_id(session, receipt_id)

            if not record or not record.status == BorrowingStatus.PENDING:
                return await ctx.send("Record does not exist or cannot be denied!")
            
            match msg.content:
                case "yes":
                    await (await self.bot.record_channel.fetch_message(record.message_id)).add_reaction("❌")
                    await (self.bot.get_guild(EC_SERVER_ID).get_member(record.user_id)).send("")
                    await BookDB.borrow(session, record.book_isbn, True)
                    await BorrowingRecordDB.disapprove_record_by_id(session, int(receipt_id))
                    await ctx.send(f"Denied **{receipt_id}**!")

                    try:
                        dm = await (self.bot.get_guild(EC_SERVER_ID).get_member(record.user_id)).create_dm()
                    except discord.Forbidden:
                        await self.bot.bot_channel.send(f"{ctx.author.mention} Your request has been debued! (I cannot send you a dm)\n**Please come to **Ruang Bahasa** afterschool!")
                    else:
                        await dm.send("Your request has been denied: Please contact the @librarian or open a ticket for more information!")
        
                case _:
                    return await ctx.send("Aborting...")

    @commands.command()
    @commands.has_role(LIBRARIAN_ROLE)
    async def renew(self, ctx: commands.Context, patron: discord.Member):
        await ctx.send(f"Renewing for **{patron.mention}**? \n**(yes, no)**")
        msg = await self.bot.wait_for("message", check=lambda msg: msg.content.lower() in ["yes", "no"] and msg.channel == ctx.channel and msg.author == ctx.author)

        match msg.content:
            case "yes":
                pass
            case _:
                return await ctx.send("Aborting...")
            
        async with AsyncSessionLocal() as session:
            record = (await BorrowingRecordDB.get_all_by_patron(session, patron.id))[0]
        
            if not record.status == BorrowingStatus.BORROWING:
                return await ctx.send("They have not borrowed any book!")
            
            await BorrowingRecordDB.renew(session, record.id)

            book = await BookDB.get_by_id(session, record.book_isbn, True)
            name, phone_number, _ = record.remarks.split(":")
            file = discord.File(
                build_renewed_receipt_image(
                    book,
                    name,
                    record.id,
                    (record.due_date).strftime(TIMEFORMAT),
                ),
                "renewed.png",
            )
            em = (
                discord.Embed(
                    title=name,
                    description=f"**{ctx.author.mention}** has renewed a book!\n\n{name} • {phone_number}",
                    color=discord.Color.yellow(),
                    timestamp=record.borrow_date,
                )
                .set_author(name=patron.name, icon_url=patron.avatar.url)
                .set_footer(text=f"Renewed by {ctx.author.name}", icon_url=ctx.author.avatar.url)
                .set_image(url="attachment://renewed.png")
                .set_thumbnail(url=book.get_cover_url("large"))
            )
            msg = await self.bot.record_channel.fetch_message(record.message_id)
            await msg.reply(embed=em, file=file)
            await ctx.send(f"`٩(>ᴗ<)و` I renewed your book!\n{patron.mention} Please come to **Language Room** to confirm your renewal after school and bring **the book**.\nThank you!")

            file = discord.File(
                build_renewed_receipt_image(
                    book,
                    name,
                    record.id,
                    (record.due_date).strftime(TIMEFORMAT),
                ),
                "renewed.png",
            )

            await patron.send(embed=em, file=file)


    @commands.command(name="return")
    @commands.has_role(LIBRARIAN_ROLE)
    async def _return(self, ctx: commands.Context, patron: discord.Member): #What if the user does not go to the library for returning the book.
        await ctx.send(f"Are they **{patron.mention}** done with the book? \n**(yes, no)**")
        msg = await self.bot.wait_for("message", check=lambda msg: msg.content.lower() in ["yes", "no"] and msg.channel == ctx.channel and msg.author == ctx.author)

        match msg.content:
            case "yes":
                pass
            case _:
                return await ctx.send("Aborting.================================..")
            
        async with AsyncSessionLocal() as session:
            record = (await BorrowingRecordDB.get_all_by_patron(session, patron.id))[0]
        
            if not record.status == BorrowingStatus.BORROWING:
                return await ctx.send("They have not borrowed any book!")
            
            book = await BookDB.get_by_id(session, record.book_isbn, True)
            await BorrowingRecordDB.finish(session, record.id)
            await BookDB.borrow(session, book.isbn, True)
            name, phone_number, _ = record.remarks.split(":")
            file = discord.File(
                build_returned_receipt_image(
                    book,
                    name,
                    record.id
                ),
                "returned.png",
            )
            em = (
                discord.Embed(
                    title=name,
                    description=f"**{ctx.author.mention}** has returned a book!\n\n{name} • {phone_number}",
                    color=discord.Color.yellow(),
                    timestamp=record.borrow_date,
                )
                .set_author(name=patron.name, icon_url=patron.avatar.url)
                .set_footer(text=f"Returned by {ctx.author.name}", icon_url=ctx.author.avatar.url)
                .set_image(url="attachment://returned.png")
                .set_thumbnail(url=book.get_cover_url("large"))
            )
            msg = await self.bot.record_channel.fetch_message(record.message_id)
            await msg.reply(embed=em, file=file)
            await ctx.send(f"`(,,⟡o⟡,,)` _`Woah!`_ Finished? already?! `( ˶° ᗜ°)!!`\nThat was fast! I hope you like the book!\n{patron.mention} Please come and return the book at the library after school!")

            file = discord.File(
                build_returned_receipt_image(
                    book,
                    name,
                    record.id
                ),
                "returned.png",
            )

            await patron.send(embed=em, file=file)

    @commands.command()
    async def rules(self, ctx: commands.Context):
        with open("policy.txt", "rb") as f:
            file = discord.File(f)

        await ctx.send(file=file)

    @commands.command()
    @commands.has_role(LIBRARIAN_ROLE)
    async def warn(self, ctx: commands.Context, patron: discord.Member, status: int, fine: int, *, remarks: str):
        async with AsyncSessionLocal() as session:
            warning = await WarningDB.create(
                session,
                patron.id,
                ctx.author.id,
                WarningType.VERBAL if status == 1 else WarningType.BLACKLIST,
                remarks,
                fine,
                False
            )

            
            await ctx.send(f"**`[{warning.id}]`**\nI have warned **{patron.name}**\nCurrently have **{await WarningDB.get_total_active_warnings(session, patron.id)} active** warnings")

    @commands.command()
    @commands.has_role(LIBRARIAN_ROLE)
    async def expire(self, ctx: commands.Context, warning_id: int):
        async with AsyncSessionLocal() as session:
            if await WarningDB.expire(
                session,
                warning_id
            ):
                await ctx.message.add_reaction("<:catyes:1441322976111890465>")

    @commands.command()
    @commands.has_role(LIBRARIAN_ROLE)
    async def add(self, ctx: commands.Context, emoji):
        async with AsyncSessionLocal() as session:
            with open("data.json", "r", encoding='utf-8') as f:
                data = json.load(f)

            
            await BookDB.add(session, emoji, data["items"][-1])
            await ctx.send("Done!")
        

async def setup(bot):
    await bot.add_cog(Library(bot))