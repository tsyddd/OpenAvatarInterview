from chat_engine.chat_engine import ChatEngine
import gradio as gr
import os
import argparse
import signal
import sys

import uvicorn
from fastapi import FastAPI
from loguru import logger

from engine_utils.directory_info import DirectoryInfo
from service.service_utils.logger_utils import config_loggers
from service.service_utils.service_config_loader import load_configs
from service.service_utils.ssl_helpers import create_ssl_context

project_dir = DirectoryInfo.get_project_dir()
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, help="service host address")
    parser.add_argument("--port", type=int, help="service host port")
    parser.add_argument("--config", type=str, default="config/interview_with_lam.yaml", help="config file to use")
    parser.add_argument("--env", type=str, default="default", help="environment to use in config file")
    return parser.parse_args()


class OpenAvatarInterviewWebServer(uvicorn.Server):
    def __init__(self, chat_engine: ChatEngine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_engine = chat_engine

    async def shutdown(self, sockets=None):
        logger.info("Start normal shutdown process")
        self.chat_engine.shutdown()
        await super().shutdown(sockets)


def setup_demo():
    app = FastAPI(docs_url=None, redoc_url=None)
    with gr.Blocks() as gradio_block:
        with gr.Column():
            with gr.Group() as rtc_container:
                pass
    gr.mount_gradio_app(app, gradio_block, "/gradio")
    return app, gradio_block, rtc_container


def main():
    args = parse_args()
    config_from_env = os.environ.get("OPEN_AVATAR_INTERVIEW_CONFIG")
    if config_from_env:
        args.config = config_from_env
    logger_config, service_config, engine_config = load_configs(args)
    config_loggers(logger_config)
    demo_app, ui, parent_block = setup_demo()
    chat_engine = ChatEngine()
    chat_engine.initialize(engine_config, app=demo_app, ui=ui, parent_block=parent_block)
    ssl_context = create_ssl_context(args, service_config)
    uvicorn_config = uvicorn.Config(demo_app, host=service_config.host, port=service_config.port, **ssl_context)
    server = OpenAvatarInterviewWebServer(chat_engine, uvicorn_config)
    server.run()


def cli() -> int:
    try:
        main()
        return 0
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, exiting.")
        return 130
    except Exception:
        logger.exception("OpenAvatarInterview failed during startup.")
        return 1
    finally:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)


if __name__ == "__main__":
    raise SystemExit(cli())
