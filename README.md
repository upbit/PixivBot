# PixivBot for Tencent Weibo

自动爬取Pixiv日榜数据，并按评分定时推送到微博的机器人。

* [2013-08-01] 新的部署方式，支持从GAE后台修改配置和bot参数。更新为IllustModel存储方式，减少抓取时的写性能消耗。

后端使用GAE搭建，用到了[tweibo-pysdk](https://github.com/upbit/tweibo-pysdk)和[pixivpy](https://github.com/upbit/pixivpy)，部署前请参考tweibo-pysdk配置config.py中的ACCESS_TOKEN和OPENID

***
部署与示例请参考[Wiki](https://github.com/upbit/PixivBot/wiki)
