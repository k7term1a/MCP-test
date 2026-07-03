from core.llm import OpenAIChat
from mcp_client import MCPClient
from core.tools import ToolManager


class Chat:
    def __init__(self, llm_service: OpenAIChat, clients: dict[str, MCPClient]):
        self.llm_service: OpenAIChat = llm_service
        self.clients: dict[str, MCPClient] = clients
        self.messages: list[dict] = []

    async def _process_query(self, query: str):
        self.messages.append({"role": "user", "content": query})

    async def run(
        self,
        query: str,
    ) -> str:
        final_text_response = ""

        await self._process_query(query)

        while True:
            response = self.llm_service.chat(
                messages=self.messages,
                tools=await ToolManager.get_all_tools(self.clients),
            )

            self.llm_service.add_assistant_message(self.messages, response)

            if response.tool_calls:
                if response.content:
                    print(response.content)
                tool_result_parts = await ToolManager.execute_tool_requests(
                    self.clients, response
                )

                self.messages.extend(tool_result_parts)
            else:
                final_text_response = self.llm_service.text_from_message(
                    response
                )
                break

        return final_text_response
