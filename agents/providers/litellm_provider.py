"""LiteLLM Provider 实现"""

import json
import os
from typing import AsyncIterator, Any, cast
from loguru import logger
from .base import LLMProvider, StreamChunk, ToolCall


def _clear_proxy_env():
    """清除代理环境变量，避免连接问题"""
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    for var in proxy_vars:
        os.environ.pop(var, None)
    os.environ['NO_PROXY'] = '*'


class LiteLLMProvider(LLMProvider):
    """LiteLLM Provider 实现"""
    
    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        api_version: str | None = None,
        default_model: str = "anthropic/claude-4.5",
        timeout: float = 120.0,
        max_retries: int = 3,
        provider_id: str | None = None,
        **kwargs: Any
    ):
        # 清除代理环境变量，避免连接问题
        _clear_proxy_env()
        
        # 在导入 litellm 之前设置环境变量，避免启动时网络请求
        os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
        
        super().__init__(api_key, api_base, default_model, timeout, max_retries)
        self.provider_id = provider_id
        self.api_version = api_version
        self._configure_litellm(api_key, api_base)
        self._suppress_litellm_logging()
    
    def _suppress_litellm_logging(self) -> None:
        """禁用 LiteLLM 日志"""
        try:
            import litellm
            import logging
            
            os.environ["LITELLM_LOG"] = "ERROR"
            litellm.suppress_debug_info = True
            setattr(litellm, "set_verbose", False)
            litellm.drop_params = True
            litellm.telemetry = False
            
            # 禁用 tiktoken 以避免编码错误
            # 这会让 LiteLLM 跳过 token 计数，直接发送请求
            os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
            
            # 禁用远程模型价格映射获取（避免启动时网络超时）
            litellm.suppress_debug_info = True
            litellm.turn_off_message_logging = True
            
            # 设置 tiktoken 缓存目录（避免 Windows 权限问题）
            try:
                import tempfile
                tiktoken_cache = os.path.join(tempfile.gettempdir(), "tiktoken_cache")
                os.makedirs(tiktoken_cache, exist_ok=True)
                os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache
            except Exception:
                pass
            
            for logger_name in ["LiteLLM", "httpx", "httpcore", "openai"]:
                logging.getLogger(logger_name).setLevel(logging.CRITICAL)
                logging.getLogger(logger_name).disabled = True
        except Exception:
            pass
    
    def _configure_litellm(self, api_key: str | None, api_base: str | None) -> None:
        """配置 LiteLLM 环境变量"""
        from .registry import find_provider_by_api_base, get_provider_metadata
        # 优先用 provider_id 精确查找（自定义 API 的 api_base 为空，无法通过 URL 匹配）
        provider_metadata = (
            get_provider_metadata(self.provider_id) if self.provider_id
            else (find_provider_by_api_base(api_base) if api_base else None)
        )
        
        if provider_metadata:
            if provider_metadata.env_key and api_key:
                os.environ[provider_metadata.env_key] = api_key
            
            effective_base = api_base or provider_metadata.default_api_base or ""
            for env_name, env_val in provider_metadata.env_extras:
                resolved = env_val.replace("{api_key}", api_key or "")
                resolved = resolved.replace("{api_base}", effective_base)
                os.environ[env_name] = resolved
        elif api_key:
            os.environ["OPENAI_API_KEY"] = api_key

    @staticmethod
    def _openai_fallback_shapes(api_base: str, model: str) -> list[tuple[str, str]]:
        """Generate candidate (api_base, model) pairs for OpenAI/Azure-compatible gateways."""
        base = (api_base or "").rstrip("/")
        candidates: list[tuple[str, str]] = []

        def add_candidate(b: str, m: str) -> None:
            if not b or not m:
                return
            pair = (b.rstrip("/"), m)
            if pair not in candidates:
                candidates.append(pair)

        # Current shape first.
        add_candidate(base, model)

        if "/openai/deployments" in base:
            # If base is .../deployments, try .../deployments/<model>
            if base.endswith("/openai/deployments"):
                add_candidate(f"{base}/{model}", model)

            # If base is .../deployments/<name>, also try parent deployments path.
            if "/openai/deployments/" in base:
                root, _, tail = base.partition("/openai/deployments/")
                deployment = tail.split("/")[0] if tail else ""
                add_candidate(f"{root}/openai/deployments", deployment or model)
                add_candidate(f"{root}/openai/deployments/{deployment}", deployment or model)
                # Some gateways expose OpenAI-compatible /openai/v1 directly.
                add_candidate(f"{root}/openai/v1", model)

        return candidates
    
    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """流式聊天补全"""
        try:
            import litellm
            
            # 清除代理环境变量，确保连接不被代理干扰
            _clear_proxy_env()
            
            # 使用用户指定的模型或默认模型
            model = model or self.default_model
            if not model:
                raise ValueError("必须指定模型或设置默认模型")
            
            logger.info(f"Calling LiteLLM: {model}, api_base: {self.api_base}")
            
            request_params: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
                "timeout": self.timeout,
            }

            effective_api_base = self.api_base
            openai_azure_mode = False

            # Azure/OpenAI gateways often expect: model=azure/<deployment>, api_base=<gateway-root>.
            if (
                self.provider_id == "openai"
                and self.api_version
                and self.api_base
                and "/openai/deployments" in self.api_base
            ):
                base_norm = self.api_base.rstrip("/")
                gateway_root = base_norm.split("/openai/deployments", 1)[0]
                deployment = str(model)
                if deployment.startswith("azure/"):
                    deployment = deployment.split("/", 1)[1]
                request_params["model"] = f"azure/{deployment}"
                effective_api_base = gateway_root
                openai_azure_mode = True
                logger.info(
                    f"Using Azure-compatible LiteLLM shape: model={request_params['model']}, api_base={effective_api_base}"
                )

            # Azure/OpenAI-compatible gateways may require explicit API version.
            if self.api_version:
                request_params["api_version"] = self.api_version
            
            # max_tokens: 0 表示不传此参数，由模型自行决定
            if max_tokens and max_tokens > 0:
                request_params["max_tokens"] = max_tokens
            
            from .registry import find_provider_by_api_base, get_provider_metadata
            
            if effective_api_base:
                # 优先用 provider_id 精确查找，自定义 API 的 api_base 无法通过 URL 匹配
                provider_metadata = (
                    get_provider_metadata(self.provider_id) if self.provider_id
                    else find_provider_by_api_base(effective_api_base)
                )
                
                if openai_azure_mode:
                    request_params["api_base"] = effective_api_base
                    request_params["api_key"] = self.api_key or "not-needed"
                elif provider_metadata:
                    if provider_metadata.litellm_prefix:
                        should_skip = any(model.startswith(prefix) for prefix in provider_metadata.skip_prefixes)
                        if not should_skip:
                            request_params["model"] = f"{provider_metadata.litellm_prefix}/{model}"
                    
                    if model in provider_metadata.model_overrides:
                        overrides = provider_metadata.model_overrides[model]
                        request_params.update(overrides)
                        logger.info(f"Applied overrides for {model}: {overrides}")
                    
                    request_params["api_base"] = effective_api_base
                    #  LiteLLM 强制要求 api_key，传占位值即可
                    request_params["api_key"] = self.api_key or "not-needed"
                else:
                    request_params["api_base"] = effective_api_base
                    request_params["api_key"] = self.api_key or "not-needed"
            elif self.api_key:
                request_params["api_key"] = self.api_key
            
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"
            
            request_params.update(kwargs)
            
            # logger.debug(f"LiteLLM params: {json.dumps({k: v for k, v in request_params.items() if k not in ['api_key', 'messages']}, ensure_ascii=False)}")
            response = None
            last_err: Exception | None = None

            # For OpenAI/Azure-style gateways, retry with a few common URL/model shapes on 404.
            if self.provider_id == "openai" and self.api_base and model and not openai_azure_mode:
                fallback_pairs = self._openai_fallback_shapes(self.api_base, str(model))
                for idx, (candidate_base, candidate_model) in enumerate(fallback_pairs, start=1):
                    attempt_params = dict(request_params)
                    attempt_params["api_base"] = candidate_base
                    attempt_params["model"] = candidate_model
                    try:
                        if idx > 1:
                            logger.warning(
                                f"Retrying LiteLLM with fallback shape #{idx}: model={candidate_model}, api_base={candidate_base}"
                            )
                        response = await litellm.acompletion(**attempt_params)
                        request_params = attempt_params
                        break
                    except Exception as e:
                        last_err = e
                        if "notfound" in str(e).lower() or "resource not found" in str(e).lower():
                            continue
                        raise
                if response is None and last_err is not None:
                    raise last_err
            else:
                response = await litellm.acompletion(**request_params)

            stream_response = cast(AsyncIterator[Any], response)
            
            tool_call_buffer: dict[str, dict[str, Any]] = {}
            reasoning_buffer = ""
            # chunk_count = 0
            
            async for chunk in stream_response:
                # chunk_count += 1
                # 记录前3个chunk，以及带有finish_reason的chunk
                # has_finish_reason = chunk.choices and chunk.choices[0].finish_reason
                # if chunk_count <= 3 or has_finish_reason:
                #     logger.debug(f"LiteLLM chunk #{chunk_count}: {chunk}")
                # if not chunk.choices:
                #     continue
                
                choice = chunk.choices[0]
                delta = choice.delta
                
                # 处理内容增量
                if hasattr(delta, "content") and delta.content:
                    yield StreamChunk(content=delta.content)
                
                # 处理推理内容（思考模型如 DeepSeek-R1、Kimi 等）
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    reasoning_buffer += delta.reasoning_content
                    yield StreamChunk(reasoning_content=delta.reasoning_content)
                
                # 处理工具调用增量
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        tc_id = getattr(tc_delta, "id", None)
                        tc_index = getattr(tc_delta, "index", 0)
                        
                        # 统一使用 index 作为 key (Kimi 模型兼容性)
                        key = f"index_{tc_index}"
                        
                        # 初始化缓冲区
                        if key not in tool_call_buffer:
                            tool_call_buffer[key] = {
                                "id": tc_id or f"call_{tc_index}",
                                "name": "",
                                "arguments": ""
                            }
                        
                        # 更新 ID (如果有)
                        if tc_id:
                            tool_call_buffer[key]["id"] = tc_id
                        
                        # 累积工具调用信息
                        if hasattr(tc_delta, "function"):
                            function = tc_delta.function
                            if hasattr(function, "name") and function.name:
                                tool_call_buffer[key]["name"] = function.name
                            if hasattr(function, "arguments") and function.arguments:
                                tool_call_buffer[key]["arguments"] += function.arguments
                
                # 检查是否完成
                if choice.finish_reason:
                    # 发送所有累积的工具调用
                    for tc_data in tool_call_buffer.values():
                        if tc_data["name"]:
                            args_str = tc_data["arguments"].strip()
                            
                            # Claude 模型可能返回空字符串而不是 "{}"
                            # 根据 OpenAI 兼容标准，空字符串应该被视为空对象
                            if not args_str:
                                arguments = {}
                            else:
                                try:
                                    arguments = json.loads(args_str)
                                except json.JSONDecodeError as e:
                                    logger.error(f"JSON parse failed: {e}, raw: {repr(args_str)}")
                                    arguments = {"raw": args_str}
                            
                            yield StreamChunk(
                                tool_call=ToolCall(
                                    id=tc_data["id"],
                                    name=tc_data["name"],
                                    arguments=arguments
                                )
                            )
                    
                    # 发送完成信号
                    usage_dict = None
                    if hasattr(chunk, "usage") and chunk.usage:
                        usage_dict = {
                            "prompt_tokens": getattr(chunk.usage, "prompt_tokens", 0),
                            "completion_tokens": getattr(chunk.usage, "completion_tokens", 0),
                            "total_tokens": getattr(chunk.usage, "total_tokens", 0),
                        }
                    
                    yield StreamChunk(
                        finish_reason=choice.finish_reason,
                        usage=usage_dict
                    )
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"LiteLLM call failed: {error_msg}")
            friendly_msg = self._format_error_message(error_msg)
            yield StreamChunk(error=friendly_msg)
    
    @staticmethod
    def _format_error_message(raw: str) -> str:
        """将 LLM 原始错误转换为用户友好提示"""
        lower = raw.lower()

        # 余额不足 / 配额耗尽（通用模式）
        if any(k in lower for k in ("429", "余额不足", "quota", "rate limit", "insufficient_quota", "insufficient balance", "资源包", "balance")):
            if "余额" in raw or "资源包" in raw or "充值" in raw or "balance" in lower:
                return "API 账户余额不足，请前往服务商控制台充值后重试。"
            return "请求过于频繁或 API 配额已用尽，请稍后重试或检查账户额度。"

        # 认证失败（通用模式）
        if any(k in lower for k in ("401", "unauthorized", "invalid.*api.*key", "authentication", "token is unusable", "invalid token", "api key")):
            return "API 密钥无效或已过期，请在设置中检查并更新密钥。"

        # 模型不存在
        if any(k in lower for k in ("404", "model not found", "model_not_found", "does not exist")):
            return "所选模型不可用，请在设置中确认模型名称是否正确。"

        # 上下文过长
        if any(k in lower for k in ("context length", "max.*token", "too long", "context_length_exceeded")):
            return "对话上下文过长，请尝试新建会话或清除历史消息。"

        # 服务端错误
        if any(k in lower for k in ("500", "502", "503", "504", "internal server error", "service unavailable")):
            return "AI 服务暂时不可用，请稍后重试。"

        # 网络 / 超时
        if any(k in lower for k in ("timeout", "connection", "network", "ssl", "timed out")):
            return "网络连接异常，请检查网络设置后重试。"

        # 兜底
        return f"AI 调用出错: {raw[:200]}"

    def get_default_model(self) -> str:
        """获取默认模型"""
        return self.default_model or "anthropic/claude-4.5"
    
    async def transcribe(
        self,
        audio_file: bytes,
        model: str = "whisper-1",
        language: str | None = None,
        **kwargs: Any
    ) -> str:
        """转录音频为文本
        
        使用 litellm 的转录功能
        
        Args:
            audio_file: 音频文件字节
            model: 转录模型
            language: 语言代码
            **kwargs: 其他参数
            
        Returns:
            转录文本
        """
        try:
            import litellm
            import tempfile
            
            # 清除代理环境变量，确保连接不被代理干扰
            _clear_proxy_env()
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                temp_file.write(audio_file)
                temp_path = temp_file.name
            
            try:
                # 准备请求参数
                request_params: dict[str, Any] = {
                    "model": model,
                    "file": open(temp_path, "rb"),
                }
                
                if language:
                    request_params["language"] = language
                
                request_params.update(kwargs)
                
                # 调用 litellm 转录
                response = await litellm.atranscription(**request_params)
                
                return response.text or ""
            
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        except Exception as e:
            raise RuntimeError(f"转录失败: {str(e)}") from e
