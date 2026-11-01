from datetime import datetime
from enum import IntEnum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class MessageType(IntEnum):
    USER = 1
    BOT = 2


class MessageState(IntEnum):
    NEW = 0
    GENERATING = 1
    FINISH = 2


class MessageItemType(IntEnum):
    TEXT = 1
    IMAGE = 2
    VOICE = 3
    FILE = 4
    VIDEO = 5


class BaseInfo(BaseModel):
    channel_version: str = "1.0.0"


class CDNMedia(BaseModel):
    encrypt_query_param: str
    aes_key: str
    encrypt_type: Optional[int] = None


class TextItem(BaseModel):
    text: str


class ImageItem(BaseModel):
    media: CDNMedia
    aeskey: Optional[str] = None
    url: Optional[str] = None
    mid_size: Optional[Union[str, int]] = None
    thumb_size: Optional[Union[str, int]] = None
    thumb_height: Optional[int] = None
    thumb_width: Optional[int] = None
    hd_size: Optional[Union[str, int]] = None


class VoiceItem(BaseModel):
    media: CDNMedia
    encode_type: Optional[int] = None
    text: Optional[str] = None
    playtime: Optional[int] = None


class FileItem(BaseModel):
    media: CDNMedia
    file_name: Optional[str] = None
    md5: Optional[str] = None
    len: Optional[str] = None


class VideoItem(BaseModel):
    media: CDNMedia
    video_size: Optional[Union[str, int]] = None
    play_length: Optional[int] = None
    thumb_media: Optional["VideoItem"] = None


class RefMessage(BaseModel):
    title: Optional[str] = None
    message_item: Optional["MessageItem"] = None


class MessageItem(BaseModel):
    type: MessageItemType
    text_item: Optional[TextItem] = None
    image_item: Optional[ImageItem] = None
    voice_item: Optional[VoiceItem] = None
    file_item: Optional[FileItem] = None
    video_item: Optional[VideoItem] = None
    ref_msg: Optional[RefMessage] = None


class WeixinMessage(BaseModel):
    message_id: int
    from_user_id: str
    to_user_id: str
    client_id: str
    create_time_ms: int
    message_type: MessageType
    message_state: MessageState
    context_token: str
    item_list: list[MessageItem]


class GetUpdatesRequest(BaseModel):
    get_updates_buf: str
    base_info: BaseInfo = Field(default_factory=BaseInfo)


class GetUpdatesResponse(BaseModel):
    ret: int = 0
    msgs: list[WeixinMessage] = Field(default_factory=list)
    get_updates_buf: str = ""
    longpolling_timeout_ms: Optional[int] = None
    errcode: Optional[int] = None
    errmsg: Optional[str] = None


class SendMessageMessage(BaseModel):
    from_user_id: str = ""
    to_user_id: str
    client_id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    message_type: MessageType = MessageType.BOT
    message_state: MessageState = MessageState.FINISH
    context_token: str
    item_list: list[MessageItem]


class SendTypingRequest(BaseModel):
    ilink_user_id: str
    typing_ticket: str
    status: Literal[1, 2]
    base_info: BaseInfo = Field(default_factory=BaseInfo)


class GetConfigResponse(BaseModel):
    typing_ticket: Optional[str] = None
    ret: Optional[int] = None
    errcode: Optional[int] = None
    errmsg: Optional[str] = None


class QrCodeResponse(BaseModel):
    qrcode: str
    qrcode_img_content: str


class QrStatusResponse(BaseModel):
    status: Literal["wait", "scaned", "confirmed", "expired"]
    bot_token: Optional[str] = None
    ilink_bot_id: Optional[str] = None
    ilink_user_id: Optional[str] = None
    baseurl: Optional[str] = None


class IncomingMessage(BaseModel):
    user_id: str
    text: str
    type: Literal["text", "image", "voice", "file", "video"]
    raw: WeixinMessage
    timestamp: datetime


class Credentials(BaseModel):
    token: str
    base_url: str
    account_id: str
    user_id: str


MessageKind = Literal["text", "image", "voice", "file", "video"]


__all__ = [
    "BaseInfo",
    "CDNMedia",
    "Credentials",
    "FileItem",
    "GetConfigResponse",
    "GetUpdatesRequest",
    "GetUpdatesResponse",
    "ImageItem",
    "IncomingMessage",
    "MessageItem",
    "MessageItemType",
    "MessageKind",
    "MessageState",
    "MessageType",
    "QrCodeResponse",
    "QrStatusResponse",
    "RefMessage",
    "SendMessageMessage",
    "TextItem",
    "VideoItem",
    "VoiceItem",
    "WeixinMessage",
]
