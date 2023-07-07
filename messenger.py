from sqlalchemy.orm import (DeclarativeBase,Mapped,mapped_column,relationship,Session)
from sqlalchemy import ForeignKey,create_engine,select
from typing import List
from config import *
from pyrogram import Client,filters
from pyrogram.types import Message as pMessage
from sqlalchemy.exc import IntegrityError
from pyrogram.errors.exceptions.bad_request_400 import UserIsBlocked
class Base(DeclarativeBase):
    ...

class User(Base):
    __tablename__ = 'user_account'

    id:Mapped[int] = mapped_column(primary_key=True)
    userid:Mapped[str] = mapped_column(unique=True)
    messages:Mapped[List['Message']] = relationship(
        cascade='all, delete-orphan',back_populates='user'
    )
    blocked:Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:
        return f'User(id={self.id!r}, userid={self.userid!r}, blocked={self.blocked!r})'



class Message(Base):
    __tablename__ = 'message'

    id:Mapped[int] = mapped_column(primary_key=True)
    user:Mapped['User'] = relationship(back_populates='messages')
    userid:Mapped[str] = mapped_column(ForeignKey('user_account.userid'))
    onwermid:Mapped[str]
    usermid:Mapped[str]

    def __repr__(self) -> str:
        return f'Message(id={self.id!r}, userid= {self.userid!r}, fromid={self.fromid!r}, toid={self.toid!r})'
    

engine = create_engine('sqlite:///mymessenger.db',echo=True)
Base.metadata.create_all(engine)


Bot = Client('mymessenger',api_id=api_id,api_hash=api_hash,bot_token=bot_token)

@Bot.on_message(~filters.chat(owner_id))
async def userAdder(client:Client , message:pMessage)->None:
    with Session(engine) as session:
        newuser = User(userid=message.chat.id)
        try:
            session.add(newuser)
            session.commit()
        except IntegrityError:
            ...
    message.continue_propagation()

@Bot.on_message(filters.command('start'))
async def start(client:Client , message:pMessage)->None:
    if(message.chat.id == owner_id):
        await message.reply('سلام سرورم!!!')
        return
    await message.reply(
        'سلام به ربات پیوی اشکان خوش اومدی\n'
        'هر پیامی داری بفرست که به دستش برسونم:)'
    )

@Bot.on_message(filters.command('block') & filters.reply & filters.chat(owner_id))
async def block(client:Client , message:pMessage)->None:
    getMessage = (select(Message)
                    .where(Message.onwermid == message.reply_to_message_id)
                )
    with Session(engine) as session:
        user = session.scalar(getMessage).user
        user.blocked = True
        session.commit()
    
    await message.reply('کاربر بلاک شد!')

@Bot.on_message(filters.command('unblock') & filters.reply & filters.chat(owner_id))
async def unblock(client:Client , message:pMessage)->None:
    getMessage = (select(Message)
                    .where(Message.onwermid == message.reply_to_message_id)
                )
    with Session(engine) as session:
        user = session.scalar(getMessage).user
        user.blocked = False
        session.commit()
    
    await message.reply('کاربر آنبلاک شد!')


@Bot.on_message(filters=filters.reply & filters.chat(owner_id))
async def sendOwnerMessage(client:Client,message:pMessage)->None:
    getMessage = (select(Message)
                    .where(Message.onwermid == message.reply_to_message_id)
                )
    with Session(engine) as session:
        ownerMessage = session.scalar(getMessage)
        try:
            sent = await message.copy(int(ownerMessage.userid),reply_to_message_id=int(ownerMessage.usermid))
        except UserIsBlocked:
            await message.reply('کاربر شما را بلاک کرده!')
            return
        
        saveMessage = Message(
            userid=ownerMessage.userid,
            onwermid=message.id,
            usermid=sent.id
        )
        session.add(saveMessage)
        session.commit()
    
    await message.reply('پیام شما با موفقیت ارسال شد!')

@Bot.on_message(~filters.chat(owner_id))
async def sendUserMessage(client:Client,message:pMessage)->None:
    getUser = select(User).where(User.userid == message.from_user.id)
    with Session(engine) as session:
        user = session.scalar(getUser)
        if(user.blocked):
            return

    if(message.reply_to_message_id):
        getMessage = (select(Message)
                        .where(Message.usermid == message.reply_to_message_id)
                    )
        with Session(engine) as session:
            userMessage = session.scalar(getMessage)
            sent = await message.copy(owner_id,reply_to_message_id=int(userMessage.onwermid))
            saveMessage = Message(
                userid=message.chat.id,
                onwermid=sent.id,
                usermid=message.id
            )
            session.add(saveMessage)
            session.commit()
    else:
        sent = await message.copy(owner_id)
        with Session(engine) as session:
            saveMessage = Message(
                userid=message.from_user.id,
                onwermid=sent.id,
                usermid=message.id
            )
            session.add(saveMessage)
            session.commit()

    await message.reply('پیام شما با موفقیت ارسال شد!')
    

    
    

Bot.run()

