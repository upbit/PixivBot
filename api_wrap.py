# -*- coding: utf-8 -*-

import os
import sys
import urllib2
import cookielib
import logging

# https://github.com/upbit/tweibo-pysdk
sys.path.insert(0, 'tweibo.zip')
from tweibo import *
# https://github.com/upbit/pixivpy
sys.path.insert(0, 'pixivpy.zip')
from pixivpy import *

from config import *
from db_util import *

# 调试开关
_DEBUG = False

def init_tweibo_api():
    """ 初始化微博API """
    oauth = OAuth2Handler()
    oauth.set_app_key_secret(APP_KEY, APP_SECRET, CALLBACK_URL)
    oauth.set_access_token(ACCESS_TOKEN)
    oauth.set_openid(OPENID)
    if (not _DEBUG):
        api = API(oauth)
    else:
        api = API(oauth, host="127.0.0.1", port=8888)
        logging.info("init tweibo app %s with proxy success!" % APP_KEY)
    return api

def init_pixiv_api(need_login=False):
    """ 初始化PIXIV API """
    if (not _DEBUG):
        pixiv_api = PixivAPI()
    else:
        pixiv_api = PixivAPI(host="127.0.0.1", port=8888)
        logging.info("init pixiv api with proxy success!")
    if (need_login):
        login_session = pixiv_api.login("login", PIXIV_USER, PIXIV_PASS, 0)
        logging.info("login pixiv, PHPSESSID: %s" % login_session)
    return pixiv_api

def download_illust(image_obj, mobile=False, headers=None):
    """ 伪装并下载指定illust """
    req_headers = headers or [
        ('Referer', image_obj.url),
        ('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.4 (KHTML, like Gecko) Ubuntu/12.10 Chromium/22.0.1229.94 Chrome/22.0.1229.94 Safari/537.4'),
      ]

    opener = urllib2.build_opener()
    opener.addheaders = req_headers
    if (not mobile):
        logging.debug("download_illust(%s)" % image_obj.imageURL)
        return opener.open(image_obj.imageURL)
    else:
        logging.debug("download_illust(%s)" % image_obj.mobileURL)
        return opener.open(image_obj.mobileURL)

def retweet_illust_by_id(illust_id, tag_name="", source="all"):
    """ 根据illust_id转发一张图片 """
    if (long(illust_id) <= 0):
        return None

    api = init_tweibo_api()
    pixiv_api = init_pixiv_api()

    illust = pixiv_api.get_illust(illust_id)
    try:
        # 先尝试上传原始图片
        upload_illust = api.upload.t__upload_pic(format="json", pic_type=2, pic=download_illust(illust))
    except Exception, e: # [To-Do] 加入失败原因判断
        # 如果失败(一般是图片太大)，尝试上传移动端的图片
        logging.error("api.upload.t__upload_pic() error: %s" % e)
        upload_illust = api.upload.t__upload_pic(format="json", pic_type=2, pic=download_illust(illust, mobile=True))
    
    if (tag_name != ""):
        content_text = "#%s# [%s] / [%s] illust_id=%s" % (tag_name, illust.title, illust.authorName, illust.id)
    else:
        content_text = "[%s] / [%s] illust_id=%s" % (illust.title, illust.authorName, illust.id)

    logging.debug("send tweet: '%s', imgurl=%s" % (content_text, upload_illust.data.imgurl))
    tweet = api.post.t__add_pic_url(format="json", content=content_text, pic_url=upload_illust.data.imgurl, clientip="10.0.0.1")

    # 将推送过的图片记录到DB
    illust_db = IllustHelper(source)
    illust_db.InsertOrUpdateIllust(illust)
    illust_db.UpdateIllustTweetId(illust.id, tweet.data.id)

    return illust, tweet

def retweet_top_illust(source="all"):
    """ 转发当前分数最高的图片 """
    illust_db = IllustHelper(source)
    top_illust = illust_db.GetUnpubIllustsRank(limit_num=1)
    return retweet_illust_by_id(top_illust.illust_id, tag_name=TWEET_TAG_NAME, source=source)

def disabel_illust_by_id(illust_id):
    illust_db = IllustHelper("all")
    # 将tweet_id填0表示屏蔽
    return illust_db.UpdateIllustTweetId(illust_id, 0)

def crawl_ranking_to_db(content, mode):
    """ 抓取指定排行榜的作品到DB """
    pixiv_api = init_pixiv_api()
    illust_db = IllustHelper(content)

    # 抓取排行榜直到拉取到的图片point小于RANK_POINT_LIMIT
    crawl_count = 0
    page = 1
    page_limit = RANK_PAGE_LIMIT
    last_point = RANK_POINT_LIMIT * 10
    while True:
        rank_images = pixiv_api.ranking(content, mode, page)
        for image in rank_images:
            last_point = image.point
            if (last_point < RANK_POINT_LIMIT):
                logging.info("point:%d < limit:%d, exit! last illust: %s" % (last_point, RANK_POINT_LIMIT, image))
                page_limit = 0     # 停止翻页并退出抓取过程
                break

            illust_db.InsertOrUpdateIllust(image)
            crawl_count += 1

        if (page_limit > 0):
            # 处理完一页的数据，翻页继续拉取
            page += 1
            page_limit -= 1
            logging.info("get next page(%d), page_limit=%d" % (page, page_limit))
        else:
            break       # 退出爬取过程

    return crawl_count, page

def crawl_ranking_log_to_db(log_date, mode):
    """ 抓取历史排行榜的作品到DB """
    pixiv_api = init_pixiv_api()
    illust_db = IllustHelper("log_%s" % mode)

    # 抓取排行榜直到拉取到的图片point小于RANK_POINT_LIMIT
    crawl_count = 0
    page = 1
    page_limit = RANK_PAGE_LIMIT
    last_point = RANK_POINT_LIMIT * 10
    while True:
        rank_images = pixiv_api.ranking_log(log_date.year, page, mode, "%.2d"%log_date.month, "%.2d"%log_date.day)
        for image in rank_images:
            last_point = image.point
            if (last_point < RANK_POINT_LIMIT):
                logging.info("point:%d < limit:%d, exit! last illust: %s" % (last_point, RANK_POINT_LIMIT, image))
                page_limit = 0     # 停止翻页并退出抓取过程
                break

            illust_db.InsertOrUpdateIllust(image)
            crawl_count += 1

        if (page_limit > 0):
            # 处理完一页的数据，翻页继续拉取
            page += 1
            page_limit -= 1
            logging.info("get next page(%d), page_limit=%d" % (page, page_limit))
        else:
            break       # 退出爬取过程

    return crawl_count, page
