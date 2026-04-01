import asyncio
import traceback
import aiohttp
import datetime
import base64
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.message_event_result import MessageChain
from astrbot.api.message_components import Plain, Image
from astrbot.api.event.filter import EventMessageType
from .news_image_generator import create_news_image_from_data


@register(
    "astrbot_plugin_daily_xxl",
    "anka",
    "anka - 每日60s新闻推送插件, 请先设置推送目标和时间, 详情见github页面!",
    "2.1.0",
)
class DailyNewsPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.target_groups = config.get("target_groups", [])
        self.push_time = config.get("push_time", "08:00")
        self.show_text_news = config.get("show_text_news", False)
        self.use_local_image_draw = config.get("use_local_image_draw", True)
        self.enable_group_album_upload = config.get("enable_group_album_upload", False)
        self.group_album_name = config.get("group_album_name", "每日新闻")
        self.group_album_strict_mode = config.get("group_album_strict_mode", False)

        # Bot实例缓存（用于定时推送）
        self._cached_bot = None

        # 启动定时任务
        self._daily_task = asyncio.create_task(self.daily_task())

    # 获取60s新闻数据
    async def fetch_news_data(self):
        """获取每日60s新闻数据

        :return: 新闻数据
        :rtype: dict
        """
        urls = [
            "https://60s.viki.moe/v2/60s",
            "https://60s.b23.run/v2/60s",
            "https://60s-api-cf.viki.moe/v2/60s",
            "https://60s-api.114128.xyz/v2/60s",
            "https://60s-api-cf.114128.xyz/v2/60s"
        ]

        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data["data"]
                        else:
                            logger.warning(f"API返回错误代码: {response.status}")
                except Exception as e:
                    logger.warning(f"[每日新闻] 从 {url} 获取数据时出错: {e}")
                    continue

    # 下载60s新闻图片
    async def download_image(self, news_data):
        """下载每日60s图片

        :param news_data: 新闻数据
        :return: 图片的base64编码
        :rtype: str
        """
        try:
            image_url = news_data["image"]
            logger.info(f"[每日新闻] 从URL下载图片: {image_url}")

            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=30)
                async with session.get(image_url, timeout=timeout) as response:
                    if response.status != 200:
                        raise Exception(f"下载图片失败，状态码: {response.status}")
                    image_data = await response.read()
                    logger.info(f"[每日新闻] 图片下载成功, 大小: {len(image_data)}字节")
                    base64_data = base64.b64encode(image_data).decode("utf-8")
                    return base64_data
        except Exception as e:
            logger.error(f"[每日新闻] 下载图片时出错: {e}")
            traceback.print_exc()
            raise

    # 生成新闻文本
    def generate_news_text(self, news_data):
        """生成新闻文本

        :param news_data: 新闻数据
        :return: 新闻文本
        :rtype: str
        """
        date = news_data["date"]
        news_items = news_data["news"]
        tip = news_data["tip"]

        text = f"【每日60秒新闻】{date}\n\n"
        for i, item in enumerate(news_items, 1):
            text += f"{i}. {item}\n"

        text += f"\n【今日提示】{tip}\n"
        text += f"数据来源: 每日60秒新闻"

        return text

    # 上传图片到群相册
    async def _try_upload_to_group_album(self, group_id: str, image_base64: str, event: AstrMessageEvent = None):
        """尝试将新闻图片上传到群相册（仅QQ平台）"""
        logger.info(f"[每日新闻] 开始尝试上传到群相册: enable={self.enable_group_album_upload}, event={'有' if event else '无'}")
        
        if not self.enable_group_album_upload:
            logger.info(f"[每日新闻] 群相册上传功能未启用，跳过上传")
            return
        
        try:
            # 获取bot实例
            bot = None
            try:
                # 方法1: 从event获取（手动命令）
                if event:
                    bot = getattr(event, "bot", None) or getattr(event, "client", None)
                
                # 方法2: 从缓存获取
                if not bot and self._cached_bot:
                    bot = self._cached_bot
                    logger.debug(f"[每日新闻] 使用缓存的bot实例")
                
                # 方法3: 从context.platform_manager获取（定时推送）
                if not bot and hasattr(self, 'context') and hasattr(self.context, 'platform_manager'):
                    try:
                        platforms = self.context.platform_manager.get_insts()
                        logger.debug(f"[每日新闻] 找到 {len(platforms)} 个平台实例")
                        
                        for platform in platforms:
                            # 尝试多种方式获取bot实例
                            bot_client = None
                            if hasattr(platform, 'get_client'):
                                bot_client = platform.get_client()
                            if not bot_client and hasattr(platform, 'bot'):
                                bot_client = platform.bot
                            if not bot_client and hasattr(platform, 'client'):
                                bot_client = platform.client
                            
                            if bot_client:
                                bot = bot_client
                                logger.info(f"[每日新闻] 从platform_manager获取到bot实例: {type(bot_client).__name__}")
                                break
                    except Exception as e:
                        logger.debug(f"[每日新闻] 从platform_manager获取bot实例失败: {e}")
                
                if not bot:
                    logger.warning(f"[每日新闻] 无法获取bot实例，跳过群相册上传")
                    return
                
                # 检查bot是否支持群相册上传API
                if not hasattr(bot, 'upload_image_to_qun_album'):
                    logger.debug(f"[每日新闻] bot不支持群相册上传API，跳过群相册上传")
                    return
            except Exception as e:
                logger.debug(f"[每日新闻] 获取bot实例失败: {e}，跳过群相册上传")
                return
            
            # 解析group_id，判断是否为QQ平台
            if ':' in group_id:
                parts = group_id.split(':')
                platform = parts[0].lower()
                # 检查是否为QQ平台：平台名称包含onebot/qq/napcat，或者消息类型是GroupMessage
                message_type = parts[1] if len(parts) > 1 else ''
                is_qq_platform = ('onebot' in platform or 'qq' in platform or 'napcat' in platform or 
                                   message_type == 'GroupMessage')
                if not is_qq_platform:
                    logger.debug(f"[每日新闻] 群组 {group_id} 不是QQ平台，跳过群相册上传")
                    return
                actual_group_id = parts[-1] if len(parts) > 1 else group_id
            else:
                # 纯数字群号，默认为QQ平台
                actual_group_id = group_id
            
            # 将base64图片保存为临时文件
            import tempfile
            import os
            
            image_data = base64.b64decode(image_base64)
            
            # 生成文件名
            now = datetime.datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            filename = f"每日新闻_{date_str}.jpg"
            
            # 创建临时文件
            fd, temp_path = tempfile.mkstemp(suffix='.jpg', prefix='daily_news_')
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(image_data)
                
                # 查找相册ID（如果指定了相册名称）
                album_id = ""
                if self.group_album_name:
                    try:
                        result = await bot.call_action("get_qun_album_list", group_id=int(actual_group_id))
                        album_list = result.get('album_list', []) if isinstance(result, dict) else []
                        logger.info(f"[每日新闻] 获取到 {len(album_list)} 个相册，查找目标: '{self.group_album_name}'")
                        
                        for album in album_list:
                            if isinstance(album, dict):
                                name = album.get('name', '')
                                aid = album.get('album_id', '')
                                logger.info(f"[每日新闻] 相册: name='{name}', aid='{aid}'")
                                if name == self.group_album_name and aid:
                                    album_id = str(aid)
                                    logger.info(f"[每日新闻] 找到相册: '{name}' -> ID: {aid}")
                                    break
                    except Exception as e:
                        logger.debug(f"[每日新闻] 获取群相册列表失败: {e}")
                    
                    # 严格模式：指定了相册名称但找不到相册ID
                    if self.group_album_strict_mode and self.group_album_name and not album_id:
                        logger.info(f"[每日新闻] 群相册严格模式：在群 {actual_group_id} 中未找到名为 '{self.group_album_name}' 的相册，停止上传")
                        return
                
                # 准备上传参数，支持多种格式
                file_path = str(temp_path)
                file_uri = f"file://{temp_path}"
                file_base64 = f"base64://{base64.b64encode(image_data).decode('ascii')}"
                
                # 尝试多种上传模式
                upload_modes = [
                    ("raw_path", file_path),
                    ("base64", file_base64),
                    ("file_uri", file_uri)
                ]
                
                last_error = None
                upload_success = False
                
                for mode_name, file_value in upload_modes:
                    try:
                        logger.debug(f"[每日新闻] 尝试上传群相册图片: 模式={mode_name}, file_type={type(file_value).__name__}")
                        await bot.upload_image_to_qun_album(
                            group_id=int(actual_group_id),
                            album_id=str(album_id),
                            album_name=str(self.group_album_name) if self.group_album_name else "",
                            file=file_value
                        )
                        logger.info(f"[每日新闻] 成功上传图片到群 {actual_group_id} 的相册（使用{mode_name}模式）")
                        upload_success = True
                        break
                    except Exception as e:
                        last_error = e
                        logger.debug(f"[每日新闻] 上传群相册失败（{mode_name}模式）: {e}")
                        continue
                
                if not upload_success and last_error:
                    error_msg = str(last_error).lower()
                    if 'not found' in error_msg or 'not support' in error_msg or '不支持' in error_msg:
                        logger.debug(f"[每日新闻] 当前OneBot实现不支持群相册上传API")
                    else:
                        logger.warning(f"[每日新闻] 上传到群相册失败: {last_error}")
                            
            except Exception as e:
                logger.error(f"[每日新闻] 上传到群相册时出错: {e}")
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                        
        except Exception as e:
            logger.error(f"[每日新闻] 群相册上传处理异常: {e}")

    # 向指定群组推送60s新闻
    async def send_daily_news(self):
        """向所有目标群组推送每日新闻"""
        try:
            news_data = await self.fetch_news_data()
            logger.debug(f"[每日新闻] 获取到的新闻数据: {news_data}")
            if not self.use_local_image_draw:
                image_data = await self.download_image(news_data)
            else:
                image_data = create_news_image_from_data(news_data, logger)
                logger.debug(
                    f"[图片生成] 生成的图片 Base64 数据前 100 字符: {image_data[:100]}"
                )

            if not self.target_groups:
                logger.info("[每日新闻] 未配置目标群组")
                return

            logger.info(
                f"[每日新闻] 准备向 {len(self.target_groups)} 个群组推送每日新闻"
            )

            for group_id in self.target_groups:
                try:
                    # 首先发送图片
                    image_message_chain = MessageChain()
                    image_message = [Image.fromBase64(image_data)]
                    image_message_chain.chain = image_message
                    logger.info(f"[每日新闻] 向群组 {group_id} 发送图片")
                    await self.context.send_message(group_id, image_message_chain)
                    
                    # 尝试上传图片到群相册（定时推送没有event，传入None）
                    await self._try_upload_to_group_album(group_id, image_data, None)

                    # 如果配置了显示文本新闻，则发送文本
                    if self.show_text_news:
                        text_message_chain = MessageChain()
                        text_news = self.generate_news_text(news_data)
                        text_message = [Plain(text_news)]
                        text_message_chain.chain = text_message
                        await self.context.send_message(group_id, text_message_chain)

                    logger.info(f"[每日新闻] 已向群 {group_id} 推送每日新闻")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"[每日新闻] 向群组 {group_id} 推送消息时出错: {e}")
                    traceback.print_exc()
        except Exception as e:
            logger.error(f"[每日新闻] 推送每日新闻时出错: {e}")
            traceback.print_exc()

    # 计算到明天指定时间的秒数
    def calculate_sleep_time(self):
        """计算到下一次推送时间的秒数"""
        now = datetime.datetime.now()
        hour, minute = map(int, self.push_time.split(":"))

        tomorrow = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if tomorrow <= now:
            tomorrow += datetime.timedelta(days=1)

        seconds = (tomorrow - now).total_seconds()
        return seconds

    # 定时任务
    async def daily_task(self):
        """定时推送任务"""
        while True:
            try:
                # 计算到下次推送的时间
                sleep_time = self.calculate_sleep_time()
                logger.info(f"[每日新闻] 下次推送将在 {sleep_time/3600:.2f} 小时后")

                # 等待到设定时间
                await asyncio.sleep(sleep_time)

                # 推送新闻
                await self.send_daily_news()

                # 再等待一段时间，避免重复推送
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"[每日新闻] 定时任务出错: {e}")
                traceback.print_exc()
                await asyncio.sleep(300)

    @filter.command("news_status")
    async def check_status(self, event: AstrMessageEvent):
        """检查插件状态"""
        now = datetime.datetime.now()
        sleep_time = self.calculate_sleep_time()
        hours = int(sleep_time / 3600)
        minutes = int((sleep_time % 3600) / 60)

        yield event.plain_result(
            f"每日60s新闻插件正在运行\n"
            f"目标群组: {', '.join(map(str, self.target_groups))} \n"
            f"推送时间: {self.push_time}\n"
            f"文本新闻显示: {'开启' if self.show_text_news else '关闭'}\n"
            f"群相册上传: {'开启' if self.enable_group_album_upload else '关闭'}\n"
            f"目标相册: {self.group_album_name if self.group_album_name else '默认相册'}\n"
            f"距离下次推送还有: {hours}小时{minutes}分钟"
        )

    @filter.command("push_news")
    async def manual_push_news(self, event: AstrMessageEvent, mode: str = "all"):
        """手动推送今日新闻

        Args:
            mode: 获取模式，可选值: image(仅图片)/text(仅文本)/all(图片+文本)
        """
        try:
            # 保存原始配置
            original_show_text = self.show_text_news

            # 根据命令参数临时调整配置
            if mode == "text":
                self.show_text_news = True  # 仅文本模式，启用文本显示
            elif mode == "image":
                self.show_text_news = False  # 仅图片模式，禁用文本显示
            elif mode == "all":
                self.show_text_news = True  # 全部模式，启用文本显示

            # 直接调用日常推送逻辑
            logger.info(f"[每日新闻] 手动触发新闻推送，模式: {mode}")
            await self.send_daily_news()

            # 恢复原始配置
            self.show_text_news = original_show_text

            yield event.plain_result(
                f"[每日新闻] 已成功向 {len(self.target_groups)} 个群组推送新闻"
            )

        except Exception as e:
            logger.error(f"[每日新闻] 手动推送新闻时出错: {e}")
            traceback.print_exc()
            yield event.plain_result(f"推送新闻失败: {str(e)}")
        finally:
            event.stop_event()

    @filter.command("get_news")
    async def manual_get_news(self, event: AstrMessageEvent, mode: str = "all"):
        """手动获取今日新闻

        Args:
            mode: 获取模式，可选值: image(仅图片)/text(仅文本)/all(图片+文本)
        """
        try:
            # 保存原始配置
            original_show_text = self.show_text_news

            # 根据命令参数临时调整配置
            if mode == "text":
                self.show_text_news = True  # 仅文本模式，启用文本显示
            elif mode == "image":
                self.show_text_news = False  # 仅图片模式，禁用文本显示
            elif mode == "all":
                self.show_text_news = True  # 全部模式，启用文本显示

            # 直接调用日常推送逻辑
            logger.info(f"[每日新闻] 手动获取新闻，模式: {mode}")
            try:
                news_data = await self.fetch_news_data()
                logger.debug(f"[每日新闻] 获取到的新闻数据: {news_data}")
                if not self.use_local_image_draw:
                    image_data = await self.download_image(news_data)
                else:
                    image_data = create_news_image_from_data(news_data, logger)
                    logger.debug(
                        f"[图片生成] 生成的图片 Base64 数据前 100 字符: {image_data[:100]}"
                    )

                logger.info(
                    f"[每日新闻] 准备向 {event.unified_msg_origin} 发送每日新闻"
                )

                try:
                    # 首先发送图片
                    image_message_chain = MessageChain()
                    image_message = [Image.fromBase64(image_data)]
                    image_message_chain.chain = image_message
                    logger.info(f"[每日新闻] 向 {event.unified_msg_origin} 发送图片")
                    await self.context.send_message(event.unified_msg_origin, image_message_chain)
                    
                    # 缓存bot实例（用于定时推送）
                    bot_instance = getattr(event, "bot", None) or getattr(event, "client", None)
                    if bot_instance:
                        self._cached_bot = bot_instance
                        logger.info(f"[每日新闻] 已缓存bot实例: {type(bot_instance).__name__}")
                    else:
                        logger.warning(f"[每日新闻] event中没有bot实例，无法缓存")
                    
                    # 尝试上传图片到群相册
                    await self._try_upload_to_group_album(event.unified_msg_origin, image_data, event)

                    # 如果配置了显示文本新闻，则发送文本
                    if self.show_text_news:
                        text_message_chain = MessageChain()
                        text_news = self.generate_news_text(news_data)
                        text_message = [Plain(text_news)]
                        text_message_chain.chain = text_message
                        await self.context.send_message(event.unified_msg_origin, text_message_chain)

                    logger.info(f"[每日新闻] 已向 {event.unified_msg_origin} 发送每日新闻")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"[每日新闻] 向 {event.unified_msg_origin} 发送消息时出错: {e}")
                    traceback.print_exc()
            except Exception as e:
                logger.error(f"[每日新闻] 发送每日新闻时出错: {e}")
                traceback.print_exc()

            # 恢复原始配置
            self.show_text_news = original_show_text

        except Exception as e:
            logger.error(f"[每日新闻] 手动获取新闻时出错: {e}")
            traceback.print_exc()
            yield event.plain_result(f"获取新闻失败: {str(e)}")
        finally:
            event.stop_event()

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        self._daily_task.cancel()
