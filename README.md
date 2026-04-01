# 📰 AstrBot Daily News

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen)](CONTRIBUTING.md)
[![Contributors](https://img.shields.io/github/contributors/anka-afk/astrbot_plugin_daily_news?color=green)](https://github.com/anka-afk/astrbot_plugin_daily_news/graphs/contributors)
[![Last Commit](https://img.shields.io/github/last-commit/anka-afk/astrbot_plugin_daily_news)](https://github.com/anka-afk/astrbot_plugin_daily_news/commits/main)

</div>

<div align="center">

[![Moe Counter](https://count.getloli.com/get/@DailyNewsPlugin?theme=moebooru)](https://github.com/anka-afk/astrbot_plugin_daily_news)

</div>

每日 60 秒新闻推送插件 - 自动推送每日热点新闻，让你的群聊成员快速了解全球大事！

## 📢 通知

### 🎉 现在支持全平台推送 (2025-5-13), 配置方式也同样更新了, 参见下方

### 🎉 现在支持本地绘制每日新闻图片(当然也可选 api, 目前 api 的信息源不再提供图片服务, 也许可以等待恢复)

## ✨ 功能特性

- 🕒 支持定时推送，每日固定时间更新
- 📊 图文并茂，内容丰富
- 🔄 支持手动触发更新
- 🎯 支持多群组推送
- 📱 同时支持图片与文字模式
- 🌐 数据源可靠稳定
- 📸 支持自动上传图片到QQ群相册（需OneBot实现支持）

# 💡 常见问题

为什么修改配置后插件不生效？

- 请确保在修改配置后重启插件以使更改生效(这是必须的)。

## 🛠️ 配置说明

在插件配置中设置以下参数:

```json
{
  "target_groups": {
    "description": "需要推送60s新闻的群组唯一标识符列表",
    "type": "list",
    "hint": "填写需要接收60s新闻推送的群组唯一标识符，如: 你的平台名称(自己起的):GroupMessage:1350989414, napcat:FriendMessage:123456, telegram:FriendMessage:123456",
    "default": ["这里填你的平台名字:GroupMessage:这里填写你的群号"]
  },
  "push_time": {
    "description": "推送时间(以服务器时区为准)",
    "type": "string",
    "hint": "填写推送的时间，如: 08:00, 12:30, 18:00",
    "default": "08:00"
  },
  "show_text_news": {
    "description": "是否显示文字新闻",
    "type": "bool",
    "hint": "是否显示文字新闻，默认隐藏",
    "default": false
  },
  "use_local_image_draw": {
    "description": "是否使用本地图片绘制",
    "type": "bool",
    "hint": "是否使用本地图片绘制，为否则使用api获取图片",
    "default": false
  },
  "enable_group_album_upload": {
    "description": "启用群相册上传（仅QQ平台）",
    "type": "bool",
    "hint": "新闻图片发送后自动上传到群相册。需要OneBot实现（如NapCat）支持群相册API",
    "default": false
  },
  "group_album_name": {
    "description": "目标群相册名称",
    "type": "string",
    "hint": "上传到群相册中的目标相册名称。留空则上传到默认相册。如果指定的相册不存在，插件将尝试自动创建",
    "default": "每日新闻"
  },
  "group_album_strict_mode": {
    "description": "群相册严格模式",
    "type": "bool",
    "hint": "开启后，当指定了相册名称但找不到对应相册时将直接终止上传，不会创建新相册或上传到默认相册",
    "default": false
  }
}
```

### 🛠️ 参数说明

下面是一份参数对照表:
| 参数名称 | 类型 | 默认值 | 描述 |
|----------------------|--------|----------------------------|--------------------------------------------------------------|
| target_groups | list | ["aiocqhttp:GroupMessage:这里填写你的群号"] | 需要推送 60s 新闻的群组唯一标识符列表 |
| push_time | string | "08:00" | 推送时间(以服务器时区为准) |
| show_text_news | bool | false | 是否显示文字新闻，默认隐藏 |
| use_local_image_draw | bool | true | 是否使用本地图片绘制，为否则使用 api 获取图片 |
| enable_group_album_upload | bool | false | 启用群相册上传（仅QQ平台） |
| group_album_name | string | "每日新闻" | 目标群相册名称 |
| group_album_strict_mode | bool | false | 群相册严格模式 |

群聊唯一标识符分为: 前缀:中缀:后缀

# AstrBot 4.0 及以后群聊前缀直接填你自己起的名字, 例如我连接了 napcat 平台, 起名字叫"困困猫", 那么前缀就是"困困猫"!

AstrBot 4.0 及以前:

**下面是所有可选的群组唯一标识符前缀:**

| 平台 | 群组唯一标识符前缀 |
|------------------|-------------------------------------|
| qq, napcat, Lagrange 之类的 | aiocqhttp |
| qq 官方 bot | qq_official |
| telegram | telegram |
| 钉钉 | dingtalk |
| gewechat 微信(虽然已经停止维护) | gewechat |
| lark | lark |
| qq webhook 方法 | qq_official_webhook |
| astrbot 网页聊天界面 | webchat |

**下面是所有可选的群组唯一标识符中缀:**

| 群组唯一标识符中缀 | 描述 |
|----------------------|--------|
| GroupMessage | 群组消息 |
| FriendMessage | 私聊消息 |
| OtherMessage | 其他消息 |

**群组唯一标识符后缀为群号, qq 号等**

下面提供部分示例:

1. napcat 平台向私聊用户 1350989414 推送消息, 我将平台命名为困困猫

   - `困困猫:FriendMessage:1350989414`

2. napcat 平台向群组 1350989414 推送消息

   - `aiocqhttp:GroupMessage:1350989414`

3. telegram 平台向私聊用户 1350989414 推送消息

   - `telegram:FriendMessage:1350989414`

4. telegram 平台向群组 1350989414 推送消息
   - `telegram:GroupMessage:1350989414`

## 📝 使用命令

### 查看插件状态

```
/news_status
```

显示当前配置的目标群组、推送时间、是否显示文字新闻，以及距离下次推送的剩余时间。

### 手动推送新闻

```
/push_news [模式]
```

支持的模式:

- `image` - 仅推送图片新闻
- `text` - 仅推送文字新闻
- `all` - 同时推送图片和文字新闻（默认）

此命令会将新闻推送到配置的所有目标群组。

### 用户手动获取新闻

```
/get_news [模式]
```

支持的模式:

- `image` - 仅推送图片新闻
- `text` - 仅推送文字新闻
- `all` - 同时推送图片和文字新闻（默认）

此命令会将新闻发送至请求获取新闻的用户会话。

## 🔄 版本历史

- v1.0.0
  - ✅ 实现基础的新闻监控与推送
  - ✅ 支持图片和文字两种模式
  - ✅ 支持定时和手动推送功能
  - ✅ 多群组推送支持
- v1.0.1
  - ✅ 修复当消息推送平台和 astrbot 不在一个环境中时不能推送图片的 bug
- v2.0
  - ✅ 支持全平台推送
  - ✅ 支持本地绘制每日新闻图片
  - ✅ 优化配置方式
- v2.1.0
  - ✅ 新增备用API域名
  - ✅ 新增用户手动获取新闻的指令
  - ✅ 修复插件卸载或停用时未销毁定时器的问题
- v2.2.0
  - ✅ 新增群相册上传功能（支持手动获取和定时推送）
  - ✅ 支持自定义相册名称和严格模式
  - ✅ 优化bot实例获取机制，确保定时推送时也能上传相册

## 💡 使用提示

1. 为获得最佳体验，建议将推送时间设置在早晨（如 08:00），帮助群成员快速了解每日新闻
2. 如果群内成员更喜欢文字阅读，可以将 `show_text_news` 设为 true
3. 使用 `/news_status` 命令可随时查看插件运行状态和下次推送时间
4. 如遇特殊情况需要立即全局推送新闻，可使用 `/push_news` 命令手动触发
5. 如用户想自行获取新闻，可使用 `/get_news` 命令手动获取
6. 群相册上传功能需要 OneBot 实现（如 NapCat、Lagrange 等）支持群相册 API，默认关闭
7. 开启群相册上传后，建议先手动测试相册名称是否正确，避免上传到错误的相册

## 👥 贡献指南

欢迎通过以下方式参与项目：

- 🐛 提交 Issue 报告问题
- 💡 提出新功能建议
- 🔧 提交 Pull Request 改进代码

## 🌟 鸣谢

- 感谢 [每日 60 秒新闻 API](https://60s-api.viki.moe/v2/60s) 提供的数据支持
- 感谢所有为这个项目做出贡献的开发者！

---

> 信息知天下，六十秒读懂世界 📰
