

import re
from typing import Dict, Optional, cast
from loguru import logger
import numpy as np
from pydantic import BaseModel, Field
from abc import ABC
import os
import torch
from chat_engine.contexts.handler_context import HandlerContext
from chat_engine.data_models.chat_engine_config_data import ChatEngineConfigModel, HandlerBaseConfigModel
from chat_engine.common.handler_base import HandlerBase, HandlerBaseInfo, HandlerDataInfo, HandlerDetail
from chat_engine.data_models.chat_data.chat_data_model import ChatData
from chat_engine.data_models.chat_data_type import ChatDataType
from chat_engine.data_models.runtime_data.data_bundle import DataBundle, DataBundleDefinition, DataBundleEntry
from chat_engine.contexts.session_context import SessionContext
from funasr import AutoModel

from engine_utils.directory_info import DirectoryInfo
from engine_utils.general_slicer import SliceContext, slice_data


class ASRConfig(HandlerBaseConfigModel, BaseModel):
    model_name: str = Field(default="iic/SenseVoiceSmall")
    device: str = Field(default="auto")


class ASRContext(HandlerContext):
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self.config = None
        self.local_session_id = 0
        self.output_audios = []
        self.audio_slice_context = SliceContext.create_numpy_slice_context(
            slice_size=16000,
            slice_axis=0,
        )
        self.cache = {}

        self.dump_audio = True
        self.audio_dump_file = None
        if self.dump_audio:
            dump_file_path = os.path.join(DirectoryInfo.get_project_dir(),
                                          "dump_talk_audio.pcm")
            self.audio_dump_file = open(dump_file_path, "wb")


class HandlerASR(HandlerBase, ABC):
    def __init__(self):
        super().__init__()

        self.model_name = 'iic/SenseVoiceSmall'
        self.device = "cpu"

    def get_handler_info(self) -> HandlerBaseInfo:
        return HandlerBaseInfo(
            name="ASR_Funasr",
            config_model=ASRConfig,
        )

    def get_handler_detail(self, session_context: SessionContext,
                           context: HandlerContext) -> HandlerDetail:
        definition = DataBundleDefinition()
        definition.add_entry(DataBundleEntry.create_audio_entry("avatar_audio", 1, 24000))
        inputs = {
            ChatDataType.HUMAN_AUDIO: HandlerDataInfo(
                type=ChatDataType.HUMAN_AUDIO,
            )
        }
        outputs = {
            ChatDataType.HUMAN_TEXT: HandlerDataInfo(
                type=ChatDataType.HUMAN_TEXT,
                definition=definition,
            )
        }
        return HandlerDetail(
            inputs=inputs, outputs=outputs,
        )

    def load(self, engine_config: ChatEngineConfigModel, handler_config: Optional[BaseModel] = None):
        requested_device = "auto"
        if isinstance(handler_config, ASRConfig):
            self.model_name = handler_config.model_name
            requested_device = handler_config.device
            model_path = os.path.join(DirectoryInfo.get_models_dir(), handler_config.model_name)
            if os.path.exists(model_path):
                self.model_name = model_path
        self.device = self._resolve_device(requested_device)
        logger.info(f"load model {self.model_name} on device {self.device}")
        try:
            self.model = AutoModel(model=self.model_name, disable_update=True, device=self.device)
        except torch.OutOfMemoryError:
            if self.device != "cpu":
                logger.warning(f"SenseVoice failed to load on {self.device} due to CUDA OOM. Falling back to CPU.")
                self.device = "cpu"
                torch.cuda.empty_cache()
                self.model = AutoModel(model=self.model_name, disable_update=True, device=self.device)
            else:
                raise
        except RuntimeError as exc:
            if self.device != "cpu" and "out of memory" in str(exc).lower():
                logger.warning(f"SenseVoice failed to load on {self.device} due to runtime OOM. Falling back to CPU.")
                self.device = "cpu"
                torch.cuda.empty_cache()
                self.model = AutoModel(model=self.model_name, disable_update=True, device=self.device)
            else:
                raise

    def _resolve_device(self, requested_device: str) -> str:
        if requested_device and requested_device != "auto":
            return requested_device
        if torch.cuda.is_available():
            return "cuda:0"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def create_context(self, session_context, handler_config=None):
        if not isinstance(handler_config, ASRConfig):
            handler_config = ASRConfig()
        context = ASRContext(session_context.session_info.session_id)
        return context

    def start_context(self, session_context, handler_context):
        pass

    def handle(self, context: HandlerContext, inputs: ChatData,
               output_definitions: Dict[ChatDataType, HandlerDataInfo]):

        output_definition = output_definitions.get(ChatDataType.HUMAN_TEXT).definition
        context = cast(ASRContext, context)
        if inputs.type == ChatDataType.HUMAN_AUDIO:
            audio = inputs.data.get_main_data()
        else:
            return

        if audio is not None:
            audio = audio.squeeze()

            logger.info('audio in')
            for audio_segment in slice_data(context.audio_slice_context, audio):
                if audio_segment is None or audio_segment.shape[0] == 0:
                    continue
                context.output_audios.append(audio_segment)

        speech_end = inputs.is_last_data
        if not speech_end:
            return

        # prefill remainder audio in slice context
        remainder_audio = context.audio_slice_context.flush()
        if remainder_audio is not None:
            if remainder_audio.shape[0] < context.audio_slice_context.slice_size:
                remainder_audio = np.concatenate(
                    [remainder_audio,
                     np.zeros(shape=(context.audio_slice_context.slice_size - remainder_audio.shape[0]))])
                context.output_audios.append(remainder_audio)
        output_audio = np.concatenate(context.output_audios)
        if context.audio_dump_file is not None:
            logger.info('dump audio')
            context.audio_dump_file.write(output_audio.tobytes())

        res = self.model.generate(input=output_audio, batch_size_s=10)
        logger.info(res)
        context.output_audios.clear()
        output_text = re.sub(r"<\|.*?\|>", "", res[0]['text'])
        if len(output_text) == 0:
            return
        output = DataBundle(output_definition)
        output.set_main_data(output_text)
        context.submit_data(output, finish_stream=True)

    def destroy_context(self, context: HandlerContext):
        pass
