import json
import aiohttp
import lxml.html

from astrbot.api.all import *

@register("random_images", "IGCrystal", "从 wenturc 获取随机图的插件", "1.1", "https://github.com/IGCrystal/astr_plugin_random_image")
class RandomImage(Star):
    async def fetch_random_html(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    raise Exception(f"请求失败，状态码: {resp.status}")
                return await resp.text()

    @filter.command("小姐姐")
    @filter.command("setu")
    @filter.command("黑丝")
    @filter.command("白丝")
    @filter.command("玉足")
    @filter.command("美女")
    @filter.command("rimg")
    @filter.command("色图")
    @filter.command("涩图")
    async def wenturc_image(self, event: AstrMessageEvent):
        # 检查消息是否包含 "--json" 标识
        json_flag = "--json" in event.get_plain_text().lower()
        random_url = "https://api.wenturc.com/index.php?page=dapi&s=random"
        try:
            html = await self.fetch_random_html(random_url)
        except Exception as e:
            yield event.plain_result(f"请求随机图片出错: {e}")
            return

        try:
            doc = lxml.html.fromstring(html)
            elements = doc.xpath('/html/body/div[5]/div/div[2]/div[1]/div[2]/div[1]/img')
            if not elements:
                yield event.plain_result("未能通过XPath找到随机图片。")
                return
            src = elements[0].get("src")
            if not src:
                yield event.plain_result("图片链接为空。")
                return
            if json_flag:
                yield event.plain_result(json.dumps({"url": src}))
            else:
                yield event.image_result(src)
        except Exception as e:
            yield event.plain_result(f"解析随机图片时出错: {e}")
