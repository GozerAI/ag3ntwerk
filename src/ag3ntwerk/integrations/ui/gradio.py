"""
Gradio Integration for ag3ntwerk.

Provides rapid web UI and API generation for ag3ntwerk agents.
Enables quick prototyping and deployment of agent interfaces.

Requirements:
    - pip install gradio

Gradio is ideal for:
    - Creating chat interfaces for agents
    - Building dashboards for monitoring
    - Exposing agent capabilities as APIs
    - Rapid prototyping of agent UIs
"""

import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class ComponentType(str, Enum):
    """Types of Gradio components."""

    TEXTBOX = "textbox"
    CHATBOT = "chatbot"
    DROPDOWN = "dropdown"
    SLIDER = "slider"
    CHECKBOX = "checkbox"
    FILE = "file"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DATAFRAME = "dataframe"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    CODE = "code"
    BUTTON = "button"


@dataclass
class GradioConfig:
    """Configuration for Gradio interface."""

    title: str = "ag3ntwerk Agent Interface"
    description: str = ""
    theme: str = "default"
    share: bool = False
    server_port: int = 7860
    server_name: str = "127.0.0.1"
    auth: Optional[tuple] = None  # (username, password)
    ssl_keyfile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    analytics_enabled: bool = False
    show_api: bool = True
    max_threads: int = 40
    favicon_path: Optional[str] = None
    css: Optional[str] = None


class GradioIntegration:
    """
    Integration with Gradio for web UI and API generation.

    Provides easy creation of web interfaces for ag3ntwerk agents.

    Example:
        integration = GradioIntegration()

        # Create a chat interface
        interface = integration.create_chat_interface(
            agent_handler=my_agent.chat,
            title="CEO Assistant",
        )

        # Launch
        interface.launch()
    """

    def __init__(self, config: Optional[GradioConfig] = None):
        """Initialize Gradio integration."""
        self.config = config or GradioConfig()
        self._interfaces: Dict[str, Any] = {}
        self._gr = None

    def _get_gradio(self):
        """Lazy load Gradio."""
        if self._gr is None:
            try:
                import gradio as gr

                self._gr = gr
            except ImportError:
                raise ImportError("Gradio not installed. Install with: pip install gradio")
        return self._gr

    def create_chat_interface(
        self,
        agent_handler: Callable,
        title: Optional[str] = None,
        description: Optional[str] = None,
        examples: Optional[List[str]] = None,
        system_message: Optional[str] = None,
    ) -> Any:
        """
        Create a chat interface for an agent.

        Args:
            agent_handler: Async function(message, history) -> response
            title: Interface title
            description: Interface description
            examples: Example prompts
            system_message: System message for the chat

        Returns:
            Gradio ChatInterface
        """
        gr = self._get_gradio()

        async def chat_wrapper(message: str, history: List[List[str]]) -> str:
            try:
                if inspect.iscoroutinefunction(agent_handler):
                    response = await agent_handler(message, history)
                else:
                    response = agent_handler(message, history)
                return response
            except Exception as e:
                logger.error(f"Chat error: {e}")
                return f"Error: {str(e)}"

        interface = gr.ChatInterface(
            fn=chat_wrapper,
            title=title or self.config.title,
            description=description or self.config.description,
            examples=examples,
            theme=self.config.theme if self.config.theme != "default" else None,
            analytics_enabled=self.config.analytics_enabled,
        )

        return interface

    def create_executive_dashboard(
        self,
        agents: Dict[str, Callable],
        title: str = "ag3ntwerk Agent Dashboard",
    ) -> Any:
        """
        Create a dashboard with tabs for multiple agents.

        Args:
            agents: Dict mapping agent names to handlers
            title: Dashboard title

        Returns:
            Gradio Blocks interface
        """
        gr = self._get_gradio()

        with gr.Blocks(
            title=title,
            theme=self.config.theme if self.config.theme != "default" else None,
            css=self.config.css,
        ) as dashboard:
            gr.Markdown(f"# {title}")

            with gr.Tabs():
                for name, handler in agents.items():
                    with gr.Tab(name):
                        chatbot = gr.Chatbot(label=f"{name} Chat")
                        msg = gr.Textbox(
                            label="Message",
                            placeholder=f"Ask {name}...",
                        )
                        clear = gr.Button("Clear")

                        async def respond(message, history, h=handler):
                            if inspect.iscoroutinefunction(h):
                                response = await h(message, history)
                            else:
                                response = h(message, history)
                            history.append((message, response))
                            return "", history

                        msg.submit(respond, [msg, chatbot], [msg, chatbot])
                        clear.click(lambda: None, None, chatbot, queue=False)

        return dashboard

    def create_task_interface(
        self,
        task_handler: Callable,
        input_components: List[Dict[str, Any]],
        output_components: List[Dict[str, Any]],
        title: str = "Task Interface",
        description: str = "",
    ) -> Any:
        """
        Create a custom task interface with specified inputs/outputs.

        Args:
            task_handler: Function to handle the task
            input_components: List of input component configs
            output_components: List of output component configs
            title: Interface title
            description: Interface description

        Returns:
            Gradio Interface
        """
        gr = self._get_gradio()

        inputs = []
        for comp in input_components:
            comp_type = comp.get("type", ComponentType.TEXTBOX)
            comp_config = {k: v for k, v in comp.items() if k != "type"}
            inputs.append(self._create_component(gr, comp_type, comp_config))

        outputs = []
        for comp in output_components:
            comp_type = comp.get("type", ComponentType.TEXTBOX)
            comp_config = {k: v for k, v in comp.items() if k != "type"}
            outputs.append(self._create_component(gr, comp_type, comp_config))

        interface = gr.Interface(
            fn=task_handler,
            inputs=inputs,
            outputs=outputs,
            title=title,
            description=description,
            theme=self.config.theme if self.config.theme != "default" else None,
            analytics_enabled=self.config.analytics_enabled,
        )

        return interface

    def _create_component(self, gr, comp_type: ComponentType, config: Dict) -> Any:
        """Create a Gradio component from type and config."""
        component_map = {
            ComponentType.TEXTBOX: gr.Textbox,
            ComponentType.CHATBOT: gr.Chatbot,
            ComponentType.DROPDOWN: gr.Dropdown,
            ComponentType.SLIDER: gr.Slider,
            ComponentType.CHECKBOX: gr.Checkbox,
            ComponentType.FILE: gr.File,
            ComponentType.IMAGE: gr.Image,
            ComponentType.AUDIO: gr.Audio,
            ComponentType.VIDEO: gr.Video,
            ComponentType.DATAFRAME: gr.Dataframe,
            ComponentType.JSON: gr.JSON,
            ComponentType.HTML: gr.HTML,
            ComponentType.MARKDOWN: gr.Markdown,
            ComponentType.CODE: gr.Code,
        }

        comp_class = component_map.get(comp_type, gr.Textbox)
        return comp_class(**config)

    def create_api_endpoint(
        self,
        handler: Callable,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        endpoint_name: str = "predict",
    ) -> Any:
        """
        Create an API endpoint for an agent function.

        Args:
            handler: Function to expose as API
            input_schema: Input parameter schema
            output_schema: Output schema
            endpoint_name: API endpoint name

        Returns:
            Gradio Interface configured for API use
        """
        gr = self._get_gradio()

        inputs = []
        for name, schema in input_schema.items():
            dtype = schema.get("type", "string")
            if dtype == "string":
                inputs.append(gr.Textbox(label=name))
            elif dtype == "number":
                inputs.append(gr.Number(label=name))
            elif dtype == "boolean":
                inputs.append(gr.Checkbox(label=name))
            elif dtype == "array":
                inputs.append(gr.JSON(label=name))
            else:
                inputs.append(gr.Textbox(label=name))

        outputs = []
        for name, schema in output_schema.items():
            dtype = schema.get("type", "string")
            if dtype == "string":
                outputs.append(gr.Textbox(label=name))
            elif dtype == "object" or dtype == "array":
                outputs.append(gr.JSON(label=name))
            else:
                outputs.append(gr.Textbox(label=name))

        interface = gr.Interface(
            fn=handler,
            inputs=inputs,
            outputs=outputs,
            title=f"API: {endpoint_name}",
            analytics_enabled=False,
        )

        return interface

    def create_file_processor(
        self,
        processor: Callable,
        accepted_types: List[str],
        title: str = "File Processor",
        description: str = "Upload a file for processing",
    ) -> Any:
        """
        Create a file upload and processing interface.

        Args:
            processor: Function(file_path) -> result
            accepted_types: List of accepted file extensions
            title: Interface title
            description: Interface description

        Returns:
            Gradio Interface
        """
        gr = self._get_gradio()

        interface = gr.Interface(
            fn=processor,
            inputs=gr.File(
                label="Upload File",
                file_types=accepted_types,
            ),
            outputs=[
                gr.Textbox(label="Result"),
                gr.JSON(label="Details"),
            ],
            title=title,
            description=description,
        )

        return interface

    def create_multi_modal_interface(
        self,
        handler: Callable,
        enable_text: bool = True,
        enable_image: bool = False,
        enable_audio: bool = False,
        enable_file: bool = False,
        title: str = "Multi-Modal Interface",
    ) -> Any:
        """
        Create a multi-modal input interface.

        Args:
            handler: Function handling multiple input types
            enable_text: Enable text input
            enable_image: Enable image input
            enable_audio: Enable audio input
            enable_file: Enable file input
            title: Interface title

        Returns:
            Gradio Blocks interface
        """
        gr = self._get_gradio()

        with gr.Blocks(title=title) as interface:
            gr.Markdown(f"# {title}")

            with gr.Row():
                with gr.Column():
                    text_input = (
                        gr.Textbox(
                            label="Text Input",
                            visible=enable_text,
                        )
                        if enable_text
                        else None
                    )

                    image_input = (
                        gr.Image(
                            label="Image Input",
                            visible=enable_image,
                        )
                        if enable_image
                        else None
                    )

                    audio_input = (
                        gr.Audio(
                            label="Audio Input",
                            visible=enable_audio,
                        )
                        if enable_audio
                        else None
                    )

                    file_input = (
                        gr.File(
                            label="File Input",
                            visible=enable_file,
                        )
                        if enable_file
                        else None
                    )

                    submit_btn = gr.Button("Submit")

                with gr.Column():
                    output = gr.Textbox(label="Response", lines=10)
                    json_output = gr.JSON(label="Structured Output")

            inputs = [i for i in [text_input, image_input, audio_input, file_input] if i]

            submit_btn.click(
                handler,
                inputs=inputs,
                outputs=[output, json_output],
            )

        return interface

    def launch(
        self,
        interface: Any,
        **kwargs,
    ) -> None:
        """
        Launch a Gradio interface.

        Args:
            interface: Gradio interface to launch
            **kwargs: Additional launch arguments
        """
        launch_config = {
            "share": self.config.share,
            "server_port": self.config.server_port,
            "server_name": self.config.server_name,
            "auth": self.config.auth,
            "ssl_keyfile": self.config.ssl_keyfile,
            "ssl_certfile": self.config.ssl_certfile,
            "show_api": self.config.show_api,
            "max_threads": self.config.max_threads,
            "favicon_path": self.config.favicon_path,
        }
        launch_config.update(kwargs)

        # Remove None values
        launch_config = {k: v for k, v in launch_config.items() if v is not None}

        interface.launch(**launch_config)

    def mount_to_fastapi(self, app: Any, interface: Any, path: str = "/") -> None:
        """
        Mount a Gradio interface to an existing FastAPI app.

        Args:
            app: FastAPI application
            interface: Gradio interface
            path: Mount path
        """
        gr = self._get_gradio()
        gr.mount_gradio_app(app, interface, path=path)
