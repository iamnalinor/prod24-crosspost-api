import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List, Type

from PIL import Image
from pyrogram import Client, types, errors, utils
from pyrogram.enums import ParseMode, ChatType, MessageMediaType
from pyrogram.storage.sqlite_storage import SQLiteStorage
from pyrogram.sync import wrap
from pyrogram.types import Dialog

from api.models import PostFile, Post, FileUploadedToTelegram

API_ID = 14214181
API_HASH = "XXX"

wrap(SQLiteStorage)

AuthID = str


@staticmethod
def Dialog__parse(client, dialog, messages, users, chats) -> "Dialog":
    dialog_channel = chats.get(utils.get_raw_peer_id(dialog.peer))
    if dialog_channel:
        is_admin = bool(getattr(dialog_channel, "admin_rights", None))
    else:
        is_admin = None

    dialog = Dialog(
        chat=types.Chat._parse_dialog(client, dialog.peer, users, chats),
        top_message=messages.get(utils.get_peer_id(dialog.peer)),
        unread_messages_count=dialog.unread_count,
        unread_mentions_count=dialog.unread_mentions_count,
        unread_mark=dialog.unread_mark,
        is_pinned=dialog.pinned,
    )
    dialog.is_admin = is_admin
    return dialog


types.Dialog._parse = Dialog__parse


@dataclass
class NeedPassword:
    auth_id: AuthID
    need_password: bool = True


class AuthorizedUser:
    user: types.User
    session_string: str
    need_password: bool = False


class TelegramAuthorizer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def ensure_event_loop():
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

    def send_code(
        self, phone_number: str, *, test_mode: bool = False
    ) -> AuthID:
        self.ensure_event_loop()
        client = Client(
            "smm-sendcode",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True,
            test_mode=test_mode,
        )

        client.connect()
        code = client.send_code(phone_number)
        client.storage.user_id(0)
        client.storage.is_bot(False)
        session_string = client.export_session_string()
        client.disconnect()

        return ":".join(
            [
                session_string,
                phone_number,
                code.phone_code_hash,  # noqa
            ]
        )

    def enter_code(
        self, auth_id: AuthID, code: str
    ) -> AuthorizedUser | NeedPassword:
        session_string, phone_number, phone_code_hash = auth_id.split(":")

        self.ensure_event_loop()
        client = Client(
            "smm-entercode",
            session_string=session_string,
        )

        client.connect()
        try:
            print(phone_number, phone_code_hash, code)
            user = client.sign_in(phone_number, phone_code_hash, code)
        except (errors.PasswordRequired, errors.SessionPasswordNeeded):
            return NeedPassword(auth_id)
        else:
            session_string = client.export_session_string()
        finally:
            client.disconnect()

        auth = AuthorizedUser()
        auth.user = user
        auth.session_string = session_string
        return auth

    def enter_password(
        self, code_hash: AuthID, password: str
    ) -> AuthorizedUser:
        session_string = code_hash.split(":")[0]

        self.ensure_event_loop()
        client = Client(
            "smm-password",
            session_string=session_string,
        )

        client.connect()
        user = client.check_password(password)
        session_string = client.export_session_string()
        client.disconnect()

        auth = AuthorizedUser()
        auth.user = user
        auth.session_string = session_string
        return auth


class TelegramPublisher:
    def __init__(self, session_string: str):
        self.ensure_event_loop()
        self.client = Client(
            "smm-publisher",
            session_string=session_string,
        )
        self._fetched_peers = False

    def __enter__(self):
        self.client.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.__exit__(exc_type, exc_val, exc_tb)

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    @staticmethod
    def ensure_event_loop():
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

    def prepare_file(
        self,
        file_path: str,
    ) -> Type[types.InputMedia]:
        extension = self.client.guess_extension(
            self.client.guess_mime_type(file_path)
        )
        logging.warning(file_path)
        logging.warning(self.client.guess_mime_type(file_path))
        logging.warning(extension)
        match extension:
            case ".jpg" | ".jpeg" | ".png":
                media_type = types.InputMediaPhoto
            case ".mp4" | ".gif":
                media_type = types.InputMediaVideo
            case ".mp3" | ".ogg":
                media_type = types.InputMediaAudio
            case _:
                media_type = types.InputMediaDocument

        if media_type is types.InputMediaPhoto:
            logging.info("Checking image size")
            img = Image.open(file_path)
            w, h = img.size
            if w > 2560 or h > 2560:
                logging.info("Resizing image")
                media_type = types.InputMediaDocument
            img.close()

        return media_type

    def publish(self, chat_id: "int | str", post: Post) -> types.Message:
        self._ensure_fetched_peers()

        preloaded = list(
            FileUploadedToTelegram.objects.filter(file__post=post)
        )

        files = list(PostFile.objects.filter(post=post))
        if len(preloaded) == 1 and files[0].is_video_note:
            message = self.client.copy_message(
                chat_id,
                preloaded[0].chat_id,
                preloaded[0].message_id,
            )
            if post.text.strip():
                message = self.client.send_message(
                    chat_id,
                    post.text,
                    parse_mode=ParseMode.HTML,
                )
            return message

        medias = []
        for i, preload in enumerate(preloaded):
            msg: types.Message = self.client.get_messages(
                preload.chat_id, preload.message_id
            )
            media_type = {
                MessageMediaType.PHOTO: types.InputMediaPhoto,
                MessageMediaType.VIDEO: types.InputMediaVideo,
                MessageMediaType.AUDIO: types.InputMediaAudio,
                MessageMediaType.DOCUMENT: types.InputMediaDocument,
            }.get(msg.media, types.InputMediaDocument)

            medias.append(
                media_type(
                    getattr(
                        msg, str(msg.media).split(".")[-1].lower()
                    ).file_id,
                    caption=(post.text if i == 0 else None),
                    parse_mode=ParseMode.HTML,
                )
            )

        if medias:
            return self.client.send_media_group(chat_id, medias)[0]

        return self.client.send_message(  # noqa
            chat_id,
            post.text,
            parse_mode=ParseMode.HTML,
        )

    def get_channels(self) -> List[types.Chat]:
        channels = []
        for dialog in self.client.get_dialogs():
            if (
                dialog.chat.type in (ChatType.SUPERGROUP, ChatType.CHANNEL)
                and dialog.is_admin
            ):
                channels.append(dialog.chat)
        self._fetched_peers = True
        return channels

    def _ensure_fetched_peers(self):
        if self._fetched_peers:
            return
        for _ in self.client.get_dialogs():
            pass
        self._fetched_peers = True

    def get_chat(self, chat_id: int) -> types.Chat:
        self._ensure_fetched_peers()
        try:
            chat_id = int(chat_id)
        except ValueError:
            pass
        chat = self.client.get_chat(chat_id)
        return chat

    def get_views_count(self, chat_id: int, message_ids: list[int]):
        self._ensure_fetched_peers()
        messages: List[types.Message] = self.client.get_messages(  # noqa
            chat_id, message_ids
        )
        return {
            message.id: message.views if message.views is not None else -1
            for message in messages
        }

    def get_actions_count(self, chat_id: int, message_ids: list[int]):
        self._ensure_fetched_peers()
        messages: list[types.Message] = self.client.get_messages(  # noqa
            chat_id, message_ids
        )
        results = {}
        reactions_dict = {}
        for message in messages:
            reactions = self._get_reactions_count(message.reactions) or 0
            forwards = message.forwards or 0
            try:
                replies = self.client.get_discussion_replies_count(  # noqa
                    chat_id, message.id
                )
            except:
                replies = 0
            reactions_dict[message.id] = reactions
            results[message.id] = (
                (reactions or 0) + (forwards or 0) + (replies or 0)
            )
        return results, reactions_dict

    def _get_reactions_count(self, obj):
        if obj is None:
            return 0
        if obj.reactions is None:
            return 0
        return len(obj.reactions)

    def get_channel_subscriber_count(self, chat_id):
        self._ensure_fetched_peers()
        return self.client.get_chat_members_count(chat_id)

    def get_engagement_rates(self, chat_id: int, message_ids: list[int]):
        self._ensure_fetched_peers()
        subs = self.get_channel_subscriber_count(chat_id)
        actions, reactions = self.get_actions_count(chat_id, message_ids)
        return {
            message_id: actions[message_id] / subs  # noqa
            for message_id in message_ids
        }, reactions

    def ensure_channel(self, title: str) -> types.Chat:
        for chat in self.get_channels():
            if chat.title == title:
                return chat
        chat = self.client.create_channel(
            title,
            description=(
                "Это технический канал сервиса crosspost. "
                "Здесь будут появляться превью и те файлы, "
                "которые вы хотите опубликовать в других каналах."
            ),
        )
        chat.archive()
        time.sleep(1)
        return chat


def preload_to_telegram(post_files: "list[PostFile]"):
    files = {}

    for file in post_files:
        for channel in file.post.target_channels.all():
            files.setdefault(channel.binding.session_string, [])
            files[channel.binding.session_string].append(file)

    for session_string, files in files.items():
        with TelegramPublisher(channel.binding.session_string) as tg:
            for post_file in files:
                logging.warning(f"Preloading file {post_file.file.path} for channel {channel.name}")
                preview = tg.ensure_channel("smm-client-preview")

                if post_file.is_video_note:
                    logging.warning("Sending video note")
                    message = tg.client.send_video_note(
                        preview.id,
                        post_file.file.path,
                    )
                    FileUploadedToTelegram.objects.create(
                        file=post_file,
                        binding=channel.binding,
                        chat_id=message.chat.id,
                        message_id=message.id,
                    )
                    continue

                media_type = tg.prepare_file(post_file.file.path)
                medias = [
                    media_type(
                        post_file.file.path,
                        caption="Этот файл был загружен в этот канал в целях быстродействия. "
                        "Не обращайте внимания. Пожалуйста, не удаляйте его.",
                    )
                ]

                logging.warning(f"Sending {media_type} file")
                message = tg.client.send_media_group(preview.id, medias)[0]
                logging.warning(f"File {post_file.file.path} uploaded to {message.chat.id}")
                FileUploadedToTelegram.objects.create(
                    file=post_file,
                    binding=channel.binding,
                    chat_id=message.chat.id,
                    message_id=message.id,
                )
                time.sleep(0.1)
