import asyncio
import base64
import json
import os
from typing import Any
from urllib.parse import urlencode

import pyaudio
import websockets
from dotenv import load_dotenv
from fastmcp import Client
from groq import AsyncGroq

load_dotenv()

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
SARVAM_WS_BASE_URL = "wss://api.sarvam.ai/speech-to-text-realtime/ws"
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:9000/mcp")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK_SIZE = 1600  # 100ms of 16-bit mono PCM at 16 kHz
PING_INTERVAL_S = 20

SYSTEM_PROMPT = (
    "Your name is loki"
    "You are a Windows voice assistant. When the user asks to open WhatsApp, "
    "YouTube, Chrome, or any other application, call the matching tool. After a tool runs, reply in "
    "one short sentence. If they are not asking to open an app, reply briefly "
    "without tools. Transcripts may be Telugu, English, or mixed."
    "Visual Studio code is also called as V.S. code, VS code, IDE."
    "Never kill the application 'File explorer', just deny the request."
)


def require_env() -> None:
    missing = [
        name
        for name, value in (
            ("SARVAM_API_KEY", SARVAM_API_KEY),
            ("GROQ_API_KEY", GROQ_API_KEY),
        )
        if not value
    ]
    if missing:
        raise SystemExit(
            f"Missing {', '.join(missing)} in the environment. Put them in .env."
        )


def mcp_tool_to_groq(tool: Any) -> dict[str, Any]:
    schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None)
    if schema is None:
        schema = {"type": "object", "properties": {}}
    elif hasattr(schema, "model_dump"):
        schema = schema.model_dump(by_alias=True, exclude_none=True)
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema,
        },
    }


def format_tool_result(result: Any) -> str:
    if result.data is not None:
        if isinstance(result.data, str):
            return result.data
        return json.dumps(result.data, default=str)
    texts: list[str] = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)
    if texts:
        return "\n".join(texts)
    if result.structured_content:
        return json.dumps(result.structured_content, default=str)
    return ""


def transcript_text(payload: dict[str, Any]) -> str:
    return (payload.get("text") or payload.get("transcript") or "").strip()


class VoicePipeline:
    def __init__(self) -> None:
        self.is_speaking = False
        self.latest_partial = ""
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.mcp = Client(MCP_SERVER_URL)
        self.groq = AsyncGroq(api_key=GROQ_API_KEY)
        self.groq_tools: list[dict[str, Any]] = []
        self._jobs: set[asyncio.Task[None]] = set()

    def start_mic_stream(self) -> None:
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        print("[Mic]: Streaming. Speak to open WhatsApp, YouTube, or Chrome.")

    def update_cli_feedback(self) -> None:
        status = "\033[92m● SPEAKING\033[0m" if self.is_speaking else "\033[90m○ LISTENING\033[0m"
        print(f"\r[{status}] {self.latest_partial}\033[K", end="", flush=True)

    async def fetch_mcp_tools(self) -> list[dict[str, Any]]:
        tools = await self.mcp.list_tools()
        converted = [mcp_tool_to_groq(tool) for tool in tools]
        names = ", ".join(tool.name for tool in tools) or "(none)"
        print(f"[MCP]: Connected. Tools: {names}")
        return converted

    async def execute_mcp_tool(self, name: str, arguments: dict[str, Any]) -> str:
        print(f"[MCP]: Calling {name}({arguments})")
        result = await self.mcp.call_tool(name, arguments or {})
        formatted = format_tool_result(result)
        print(f"[MCP]: {formatted}")
        return formatted

    async def process_user_text(self, text: str) -> None:
        print(f"[LLM]: {text}")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        kwargs: dict[str, Any] = {"model": GROQ_MODEL, "messages": messages}
        if self.groq_tools:
            kwargs["tools"] = self.groq_tools
            kwargs["tool_choice"] = "auto"

        response = await self.groq.chat.completions.create(**kwargs)
        message = response.choices[0].message

        if message.tool_calls:
            messages.append(message)
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    tool_args = {}
                if not isinstance(tool_args, dict):
                    tool_args = {}
                try:
                    tool_result = await self.execute_mcp_tool(tool_name, tool_args)
                except Exception as exc:
                    tool_result = f"Tool failed: {exc}"
                    print(f"[MCP Error]: {exc}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result,
                    }
                )
            final = await self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
            )
            print(f"[Agent]: {final.choices[0].message.content}")
        else:
            print(f"[Agent]: {message.content}")

    def _track(self, task: asyncio.Task[None]) -> None:
        self._jobs.add(task)
        task.add_done_callback(self._jobs.discard)

    async def receive_transcripts(self, ws: Any) -> None:
        try:
            async for raw in ws:
                data = json.loads(raw)
                event_type = data.get("event")

                if event_type == "error" or "error" in data and event_type is None:
                    err = data.get("error", data)
                    print(f"\n[STT Error]: {err}")
                    if isinstance(err, dict) and err.get("is_fatal"):
                        break
                    continue

                if event_type == "vad.speech_start":
                    self.is_speaking = True
                elif event_type == "vad.speech_end":
                    self.is_speaking = False
                elif event_type == "transcript.partial":
                    self.latest_partial = transcript_text(data)
                    self.is_speaking = True
                elif event_type == "transcript.final":
                    user_text = transcript_text(data)
                    print(f"\n[STT Final]: {user_text}")
                    self.latest_partial = ""
                    self.is_speaking = False
                    if user_text:
                        self._track(asyncio.create_task(self.process_user_text(user_text)))
        except websockets.exceptions.ConnectionClosed as exc:
            print(f"\n[STT]: Connection closed. Code: {exc.code}, Reason: {exc.reason}")

    async def send_audio(self, ws: Any) -> None:
        assert self.stream is not None
        while True:
            chunk = await asyncio.to_thread(
                self.stream.read, CHUNK_SIZE, False
            )
            payload = {
                "event": "audio_input",
                "audio": base64.b64encode(chunk).decode("utf-8"),
            }
            await ws.send(json.dumps(payload))
            self.update_cli_feedback()

    async def keepalive(self, ws: Any) -> None:
        while True:
            await asyncio.sleep(PING_INTERVAL_S)
            await ws.send(json.dumps({"event": "ping"}))

    async def run(self) -> None:
        try:
            async with self.mcp:
                self.groq_tools = await self.fetch_mcp_tools()
                self.start_mic_stream()

                query = urlencode(
                    {
                        "language_code": "auto",
                        "model": "saaras:v4",
                        "mode": "transcribe",
                        "endpointing": "vad",
                        "encoding": "linear16",
                        "sample_rate": str(RATE),
                        "stream_type": "fast",
                        "silence_duration_ms": "700",
                    }
                )
                ws_url = f"{SARVAM_WS_BASE_URL}?{query}"
                headers = {"api-subscription-key": SARVAM_API_KEY}

                async with websockets.connect(ws_url, additional_headers=headers) as sarvam_ws:
                    print("[STT]: Sarvam realtime connected.")
                    await asyncio.gather(
                        self.receive_transcripts(sarvam_ws),
                        self.send_audio(sarvam_ws),
                        self.keepalive(sarvam_ws),
                    )
        except KeyboardInterrupt:
            print("\nPipeline stopped.")
        except Exception as exc:
            print(f"\n[Pipeline Exception]: {exc}")
            if "failed to connect" in str(exc).lower() or "10061" in str(exc) or "ConnectError" in type(exc).__name__:
                print("Start the MCP server first: uv run main.py")
        finally:
            await self._shutdown_jobs()
            self.cleanup()

    async def _shutdown_jobs(self) -> None:
        if not self._jobs:
            return
        for job in list(self._jobs):
            job.cancel()
        await asyncio.gather(*self._jobs, return_exceptions=True)

    def cleanup(self) -> None:
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        try:
            self.p.terminate()
        except Exception:
            pass
        print("\n[Mic]: Closed.")


if __name__ == "__main__":
    require_env()
    try:
        asyncio.run(VoicePipeline().run())
    except KeyboardInterrupt:
        print("\nPipeline stopped.")
