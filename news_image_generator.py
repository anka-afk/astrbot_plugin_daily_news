import os
import datetime
import base64
import textwrap
from io import BytesIO
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
from .config import CURRENT_DIR
import traceback

# --- 配置常量 ---
BASE_IMAGE_DIR = os.path.join(CURRENT_DIR, "assets")
FONT_NEWS_PATH = os.path.join(BASE_IMAGE_DIR, "微软雅黑.ttf")
FONT_DATE_PATH = os.path.join(BASE_IMAGE_DIR, "2.ttf")
TEXT_COLOR = (0, 0, 0)  # 文本颜色 (黑色)

# --- 布局常量 ---
MARGIN_X = 30  # 左右边距
DATE_YEAR_POS = (855, 600)
DATE_MD_RIGHT_MARGIN = 38
DATE_MD_Y = 630

NEWS_START_Y = 690
NEWS_LINE_SPACING = 8  # 行间距
NEWS_ITEM_SPACING = 15  # 不同新闻条目之间的垂直间距
TIP_START_Y_BELOW_NEWS = 25
TIP_MAX_Y = 1860
TIP_LINE_SPACING = 6


def wrap_text_pixel(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    line_spacing: int,
) -> Tuple[str, int]:
    """
    根据像素宽度智能换行文本
    :return: (换行后的文本字符串, 文本块的总高度)
    """
    lines = []
    initial_words = []
    for paragraph in text.split("\n"):
        words_in_paragraph = []
        current_word = ""
        for char in paragraph:
            if "\u4e00" <= char <= "\u9fff":
                if current_word:
                    words_in_paragraph.append(current_word)
                words_in_paragraph.append(char)
                current_word = ""
            else:
                current_word += char
        if current_word:
            words_in_paragraph.append(current_word)

        processed_words = []
        for word in words_in_paragraph:
            if len(word) > 10 and not ("\u4e00" <= word[0] <= "\u9fff"):
                estimated_char_width = font.size * 0.6
                wrap_width_chars = max(1, int(max_width / estimated_char_width))
                processed_words.extend(
                    textwrap.wrap(
                        word,
                        width=wrap_width_chars,
                        break_long_words=True,
                        replace_whitespace=False,
                    )
                )
            else:
                processed_words.append(word)

        initial_words.extend(processed_words)
        initial_words.append("\n")

    initial_words.pop()

    current_line = ""
    for word in initial_words:
        if word == "\n":
            lines.append(current_line)
            current_line = ""
            continue

        separator = (
            " "
            if current_line
            and not ("\u4e00" <= word[0] <= "\u9fff")
            and not ("\u4e00" <= current_line[-1] <= "\u9fff")
            else ""
        )
        test_line = current_line + separator + word
        try:
            text_width = font.getlength(test_line)
        except AttributeError:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
            try:
                text_width = font.getlength(current_line)
            except AttributeError:
                bbox = draw.textbbox((0, 0), current_line, font=font)
                text_width = bbox[2] - bbox[0]

            while text_width > max_width and len(current_line) > 1:
                current_line = current_line[:-1]
                try:
                    text_width = font.getlength(current_line)
                except AttributeError:
                    bbox = draw.textbbox((0, 0), current_line, font=font)
                    text_width = bbox[2] - bbox[0]

    if current_line:
        lines.append(current_line)

    final_text = "\n".join(lines)
    if not final_text:
        return "", 0

    bbox_multi = draw.multiline_textbbox(
        (0, 0), final_text, font=font, spacing=line_spacing
    )
    actual_height = bbox_multi[3] - bbox_multi[1]

    return final_text, actual_height


def create_news_image_from_data(news_api_data: Dict[str, Any], logger) -> Optional[str]:
    try:
        date_str = news_api_data.get("date")
        news_list = news_api_data.get("news", [])
        tip = news_api_data.get("tip", "")

        if not date_str or not news_list:
            logger.error("[新闻图片生成] 缺少必要的新闻数据或日期")
            return None

        try:
            news_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            year_str = news_date.strftime("%Y年")
            month_str = news_date.strftime("%m月")
            day_str = news_date.strftime("%d日")
            day_of_week = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][news_date.weekday()]
        except ValueError as e:
            logger.error(f"[新闻图片生成] 日期格式错误: {e}")
            return None

        base_image_filename = f"60s_{day_of_week}.jpg"
        base_image_path = os.path.join(BASE_IMAGE_DIR, base_image_filename)

        if not os.path.exists(base_image_path):
            logger.warning(f"[新闻图片生成] 找不到基础图片文件: {base_image_path}")
            default_image_path = os.path.join(BASE_IMAGE_DIR, "60s_default.jpg")
            if os.path.exists(default_image_path):
                base_image_path = default_image_path
                logger.info(f"[新闻图片生成] 使用默认基础图片: {default_image_path}")
            else:
                logger.error("[新闻图片生成] 找不到默认基础图片")
                return None

        image = Image.open(base_image_path).convert("RGB")
        width, height = image.size
        draw = ImageDraw.Draw(image)

        if not os.path.exists(FONT_NEWS_PATH) or not os.path.exists(FONT_DATE_PATH):
            logger.error("[新闻图片生成] 字体文件缺失")
            return None

        try:
            font_news = ImageFont.truetype(FONT_NEWS_PATH, 27)
            font_date = ImageFont.truetype(FONT_DATE_PATH, 20)
            font_quote = ImageFont.truetype(FONT_NEWS_PATH, 23)
        except IOError as e:
            logger.error(f"[新闻图片生成] 加载字体文件失败: {e}")
            return None

        draw.text(DATE_YEAR_POS, year_str, fill=TEXT_COLOR, font=font_date)
        month_day_str = f"{month_str}{day_str}"
        month_day_bbox = draw.textbbox((0, 0), month_day_str, font=font_date)
        month_day_width = month_day_bbox[2] - month_day_bbox[0]
        month_day_x = width - month_day_width - DATE_MD_RIGHT_MARGIN
        draw.text(
            (month_day_x, DATE_MD_Y), month_day_str, fill=TEXT_COLOR, font=font_date
        )

        max_news_width = width - 2 * MARGIN_X
        current_y = NEWS_START_Y

        for i, item in enumerate(news_list):
            item = item.strip()
            numbered_item = f"{i + 1}. {item}"

            wrapped_item, _ = wrap_text_pixel(
                draw, numbered_item, font_news, max_news_width, NEWS_LINE_SPACING
            )

            if not wrapped_item:
                continue

            draw.text(
                (MARGIN_X, current_y),
                wrapped_item,
                fill=TEXT_COLOR,
                font=font_news,
                spacing=NEWS_LINE_SPACING,
            )

            item_bbox = draw.multiline_textbbox(
                (MARGIN_X, current_y),
                wrapped_item,
                font=font_news,
                spacing=NEWS_LINE_SPACING,
            )
            item_height = item_bbox[3] - item_bbox[1]

            current_y += item_height + NEWS_ITEM_SPACING

            if current_y > TIP_MAX_Y:
                logger.warning(f"[新闻图片生成] 警告: 新闻内容将越界, 位于: {i+1}.")

        last_news_bottom_y = current_y - NEWS_ITEM_SPACING

        if tip:
            tip_full_text = f"【微语】{tip.strip()}"
            max_tip_width = width - 2 * MARGIN_X
            wrapped_tip, _ = wrap_text_pixel(
                draw, tip_full_text, font_quote, max_tip_width, TIP_LINE_SPACING
            )

            tip_start_y = last_news_bottom_y + TIP_START_Y_BELOW_NEWS

            tip_render_bbox = draw.multiline_textbbox(
                (MARGIN_X, tip_start_y),
                wrapped_tip,
                font=font_quote,
                spacing=TIP_LINE_SPACING,
            )

            if tip_render_bbox[3] > TIP_MAX_Y:
                logger.warning(
                    f"[新闻图片生成] 警告: Tip可能越界 底边位于: {tip_render_bbox[3]}, 最大值: {TIP_MAX_Y}."
                )

            if tip_start_y < TIP_MAX_Y:
                draw.text(
                    (MARGIN_X, tip_start_y),
                    wrapped_tip,
                    fill=TEXT_COLOR,
                    font=font_quote,
                    spacing=TIP_LINE_SPACING,
                )
            else:
                logger.warning(
                    f"[新闻图片生成] 跳过Tip绘制因为达到最大y值 ({tip_start_y})."
                )

        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="JPEG", quality=88)
        img_bytes = img_byte_arr.getvalue()

        # 转换为 Base64 编码
        base64_data = base64.b64encode(img_bytes).decode("utf-8")
        logger.info("[新闻图片生成] 新闻图片生成成功")
        return base64_data

    except FileNotFoundError as e:
        logger.error(f"[新闻图片生成] 文件未找到: {e}")
        return None
    except Exception as e:
        logger.error(f"[新闻图片生成] 未知错误: {e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import logging

    # 配置日志记录
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("news_image_generator")

    # 示例数据
    example_api_data = {
        "date": "2025-05-13",
        "news": [
            "中国天气网：北方升温模式持续，预计16日起将出现大面积高温天气，局地最高气温或达40°C",
            "西藏拉孜12日发生5.5级地震：震感明显，无人员伤亡；腾讯宣布：微信、QQ地震预警功能正式覆盖至全国，iOS待解锁",
            "教育部基础教育教指委：小学阶段禁止学生独自使用开放式内容生成功能",
            "国内首例侵入式脑机接口系统前瞻性临床试验：受试者已能用意念玩赛车游戏，产品预计2028年上市",
            "江西吉水县一00后自愿入伍后拒服兵役，官方通报：不得考公，两年内经商、升学等受限",
            "民企老板被错羁212天：申请国赔千万余元，要求恢复名誉赔礼道歉",
            "湖南长沙县一出租房疑存非法代孕手术室实验室？官方通报：查封涉事场所，相关人员被控制",
            "沈阳一超市疑借领养名义烹食流浪狗，市监局回应：已收到多起投诉",
            "台媒：台当局将96%汉人改成“其余人口”，被痛批干脆改成火星来的",
            "中美日内瓦经贸会谈联合声明发布：双方同意相互取消91%的关税，暂停90天24%关税，并继续协商解决彼此关切",
            "美媒：特朗普将签署行政令，强制执行“最惠国”药价令，美国药价或将狂降30%至80%",
            "美媒：特朗普拟接受卡塔尔赠送豪华飞机，替换40年机龄的空军一号，价值4亿美元或为该国史上最贵礼物，白宫前顾问称收外国所赠专机或违宪",
            "西媒：西班牙一城市工厂发生火灾致有毒气体氯气泄漏，当局要求受影响的5个城市超过16万居民居家 “隔离”",
            "英媒：英国首相宣布永久居留权的最低居住年限将从5年延长至10年；英国首相住所起火，无人伤亡，警方紧急调查情况",
            "外媒：库尔德工人党宣布解散并结束武装活动，土耳其40年内乱结束；泽连斯基称将前往土耳其与普京会面，乌克兰已做好与俄会谈准备",
        ],
        "tip": "现实和理想之间，不变的是跋涉，暗淡与辉煌之间，不变的是开拓。这是一个比较长的例子，用来测试换行和是否会超出边界。",
    }

    # 调用新闻图片生成函数
    logger.info("[测试] 开始生成新闻图片...")
    image_base64 = create_news_image_from_data(example_api_data, logger)

    if image_base64:
        try:
            # 将 Base64 数据解码并保存为图片文件
            output_filename = "generated_news_test.jpg"
            with open(output_filename, "wb") as f:
                f.write(base64.b64decode(image_base64))
            logger.info(f"[测试] 新闻图片生成成功，已保存为 {output_filename}")
        except Exception as e:
            logger.error(f"[测试] 保存图片时发生错误: {e}")
    else:
        logger.error("[测试] 新闻图片生成失败，返回值为 None")
