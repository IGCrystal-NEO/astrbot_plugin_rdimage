import os
import asyncio
import aiohttp
import logging
import tempfile

from astrbot.api.all import AstrMessageEvent, Context, Image, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star
import astrbot.api.message_components as Comp

logger = logging.getLogger("astrbot")

@register("random_image_plugin", "IGCrystal", "从wenturc获取随机图片的插件（无 HTML 解析）", "1.2")
class RandomImagePlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.cd = 10  # 默认冷却时间为 10 秒
        self.last_usage = {}  # 记录每个用户上次使用命令的时间
        self.semaphore = asyncio.Semaphore(5)  # 限制并发请求数量为 5

    @filter.command("random_image")
    async def random_image(self, event: AstrMessageEvent):
        """
        直接获取图片数据（无 HTML 解析），下载图片后发送，最后删除临时文件。
        """
        user_id = event.get_sender_id()
        now = asyncio.get_event_loop().time()
        if user_id in self.last_usage and (now - self.last_usage[user_id]) < self.cd:
            remaining = self.cd - (now - self.last_usage[user_id])
            yield event.plain_result(f"冷却中喵～请等待 {remaining:.1f} 秒后重试。")
            return

        # **修正：先请求 JSON，解析 URL**
        json_url = "https://api.wenturc.com/index.php?json"  # 获取 JSON 数据的 API
        
        try:
            async with aiohttp.ClientSession() as session:
                # **请求 JSON，获取图片 URL**
                async with session.get(json_url) as json_resp:
                    if json_resp.status != 200:
                        yield event.plain_result("请求随机图片 JSON 失败喵～，请稍后重试。")
                        logger.info(f"API 返回数据: {json_data}")
                        return

                    json_data = await json_resp.json()  # 解析 JSON
                    image_url = json_data.get("url", "")

                    if not image_url:
                        yield event.plain_result("JSON 返回的数据中没有 URL 喵～。")
                        return

                    # **修正 URL，确保是绝对路径**
                    if image_url.startswith("./") or image_url.startswith("/./"):
                        image_url = "https://api.wenturc.com" + image_url.lstrip(".")

                    logger.info(f"解析到图片地址: {image_url}")

                # **请求图片**
                async with session.get(image_url, allow_redirects=True) as resp:
                    if resp.status != 200:
                        yield event.plain_result(f"请求随机图片失败喵～，HTTP 状态码：{resp.status}。请稍后重试。")
                        return

                    content_type = resp.headers.get("Content-Type", "")
                    if "image" not in content_type:
                        yield event.plain_result("返回内容不是图片喵～。")
                        return

                    # 读取图片二进制数据
                    image_data = await resp.read()
        except Exception as e:
            yield event.plain_result(f"请求随机图片出错喵～: {e}")
            return

        # **根据 Content-Type 确定文件后缀**
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp"
        }
        file_ext = ".jpg"  # 默认后缀
        for key, ext in ext_map.items():
            if key in content_type:
                file_ext = ext
                break

        # **下载图片到临时文件**
        try:
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, "random_image" + file_ext)
            with open(temp_file_path, "wb") as f:
                f.write(image_data)
            logger.info(f"图片已下载至: {temp_file_path}")
        except Exception as e:
            yield event.plain_result(f"保存图片时出错喵～: {e}")
            return

        # **更新用户使用时间**
        self.last_usage[user_id] = now

        # **发送图片**
        try:
            chain = [
                Comp.At(qq=event.get_sender_id()),
                Comp.Plain("来啦，给你一张随机图片喵～："),
                Comp.Image.fromFileSystem(temp_file_path)
            ]
            yield event.chain_result(chain)
        except Exception as e:
            yield event.plain_result(f"发送图片时出错喵～: {e}")
        finally:
            # **删除临时文件**
            try:
                os.remove(temp_file_path)
                logger.info(f"已删除临时图片文件: {temp_file_path}")
            except Exception as e:
                logger.error(f"删除临时文件失败喵～: {e}")

    @filter.command("random_image_help")
    async def random_image_help(self, event: AstrMessageEvent):
        help_text = """
        **随机图片插件帮助**

        **可用命令:**
        - `/random_image`
          发送一张随机图片喵～。
        - `/random_image_help` 查看此帮助信息。

        **说明:**
        - 该插件先请求 JSON 获取图片 URL，再下载图片。
        - 图片下载后会自动删除临时文件，确保不占用多余存储。
        - 默认冷却时间为 10 秒，防止刷屏喵～。
        """
        yield event.plain_result(help_text)
