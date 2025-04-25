from sqlalchemy import delete, select, func
from sqlalchemy.orm import Session
from shy_sh.manager.sql_models import Chat, ExecutedScript, ScriptType


class ChatManager:
    def __init__(self, session: Session):
        self.session = session

    def get_chat(self, chat_id):
        return self.session.get(Chat, chat_id)

    def get_all_chats(self):
        return (
            self.session.execute(select(Chat).order_by(Chat.created_at)).scalars().all()
        )

    def get_recent_scripts(
        self,
        script_type: ScriptType | None = None,
        limit: int = 20,
    ):
        q = (
            select(
                ExecutedScript.script,
                func.count(ExecutedScript.script),
                func.max(ExecutedScript.type),
                func.max(ExecutedScript.created_at),
            )
            .group_by(ExecutedScript.script)
            .order_by(ExecutedScript.created_at.desc())
            .limit(limit)
        )
        if script_type:
            q = q.where(ExecutedScript.type == script_type)
        return self.session.execute(q).all()

    def save_chat(
        self,
        id: int | None = None,
        **kwargs,
    ):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if id:
            chat = self.get_chat(id)
            if not chat:
                raise ValueError(f"Chat with ID {id} not found.")
            for key, value in kwargs.items():
                setattr(chat, key, value)
        else:
            chat = Chat(**kwargs)
            self.session.add(chat)

    def truncate_chats(self, keep: int = 100):
        self.session.execute(
            delete(Chat).where(
                Chat.id.not_in(
                    select(Chat.id).order_by(Chat.created_at.desc()).limit(keep)
                )
            )
        )
