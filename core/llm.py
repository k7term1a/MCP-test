from openai import OpenAI
from openai.types.chat import ChatCompletionMessage


class OpenAIChat:
    def __init__(self, model: str, base_url: str | None = None):
        self.client = OpenAI(base_url=base_url) if base_url else OpenAI()
        self.model = model

    def add_user_message(self, messages: list, message):
        content = (
            message.content if isinstance(message, ChatCompletionMessage) else message
        )
        messages.append({"role": "user", "content": content})

    def add_assistant_message(self, messages: list, message):
        if isinstance(message, ChatCompletionMessage):
            messages.append(message.model_dump(exclude_none=True))
        else:
            messages.append({"role": "assistant", "content": message})

    def text_from_message(self, message: ChatCompletionMessage) -> str:
        return message.content or ""

    def chat(
        self,
        messages,
        system=None,
        temperature=1.0,
        stop_sequences=None,
        tools=None,
    ) -> ChatCompletionMessage:
        full_messages = (
            [{"role": "system", "content": system}] if system else []
        ) + messages

        params = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
        }

        if stop_sequences:
            params["stop"] = stop_sequences

        if tools:
            params["tools"] = tools

        completion = self.client.chat.completions.create(**params)
        return completion.choices[0].message
