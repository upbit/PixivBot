# -*- coding: utf-8 -*-

import os
import sys
import time
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

def download_illust(image_obj, mobile=False, page=0, headers=None):
    """ 伪装并下载指定illust """
    req_headers = headers or [
        ('Referer', image_obj.url),
        ('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.4 (KHTML, like Gecko) Ubuntu/12.10 Chromium/22.0.1229.94 Chrome/22.0.1229.94 Safari/537.4'),
      ]

    opener = urllib2.build_opener()
    opener.addheaders = req_headers
    if (not mobile):
        if (image_obj.pages > 0):
            try:
                image_URL = image_obj.pageURL[page]
            except:
                image_URL = image_obj.imageURL
        else:
            image_URL = image_obj.imageURL
    else:
        image_URL = image_obj.mobileURL

    logging.debug("download_illust(%s)" % (image_URL))
    return opener.open(image_URL)

def retweet_illust_by_id(illust_id, tag_name="", source="all"):
    """ 根据illust_id转发一张图片 """
    if (long(illust_id) <= 0):
        return None, None

    api = init_tweibo_api()
    pixiv_api = init_pixiv_api()

    try:
        illust = pixiv_api.get_illust(illust_id)
    except Exception, e:
        logging.warn("pixiv_api.get_illust(%d) error: %s, retry" % (illust_id, e))
        illust = pixiv_api.get_illust(illust_id)

    if not illust:
        # 因为种种原因pixiv没有返回数据，屏蔽该作品
        logging.warn("pixiv_api.get_illust(%d) return None, illust maybe deleted." % (illust_id))
        disabel_illust_by_id(illust_id)
        return None, None

    retry_num = 2           # 最多重试2次
    size_error = False
    if (illust.pages == 0):
        while (retry_num > 0):
            # 先尝试上传原始图片
            try:
                upload_illust = api.upload.t__upload_pic(format="json", pic_type=2, pic=download_illust(illust))
                retry_num = 0
                break           # 上传成功后退出
            except TWeiboError, e:
                if e.result:
                    if (int(e.result.errcode) == 9) and (e.result.ret == 1):
                        # 如果失败原因是(errcode=9, ret=1, msg:error pic size)，尝试上传移动端的图片
                        logging.warn("api.upload.t__upload_pic() error: %s, try upload mobile pic" % e)
                        upload_illust = api.upload.t__upload_pic(format="json", pic_type=2, pic=download_illust(illust, mobile=True))
                        size_error = True
                        break

                retry_num -= 1
                time.sleep(3.1)
                logging.error("api.upload.t__upload_pic() error: %s, retry last %d" % (e, retry_num))


        if (tag_name != ""):
            content_text = "#%s# [%s] / [%s] illust_id=%s %s" % (tag_name, illust.title, illust.authorName, illust.id, illust.url)
        else:
            content_text = "[%s] / [%s] illust_id=%s %s" % (illust.title, illust.authorName, illust.id, illust.url)
        if size_error:
            content_text += " (mobile size)"

        try:
            tweet = api.post.t__add_pic_url(format="json", content=content_text, pic_url=upload_illust.data.imgurl, clientip="10.0.0.1")
        except TWeiboError, e:
            logging.error("api.post.t__add_pic_url(%s) error: %s, retry" % (upload_illust.data.imgurl, e))
            if e.body: logging.error("http body: %s" % e.body)
            time.sleep(1.2)
            tweet = api.post.t__add_pic_url(format="json", content=content_text, pic_url=upload_illust.data.imgurl, clientip="10.0.0.1")

        logging.debug("send tweet: '%s', imgurl=%s" % (content_text, upload_illust.data.imgurl))

    else:
        # 有多张时，抓取前4张图片(太多可能因为超时被GAE终止)
        page_url = []

        size_error = False
        for i in range(illust.pages):
            if (i >= 4): break

            try:
                # 上传 page(i) 的图像
                upload_illust = api.upload.t__upload_pic(format="json", pic_type=2, pic=download_illust(illust, page=i))
                page_url.append(upload_illust.data.imgurl)

            except Exception, e: # [To-Do] 加入失败原因判断
                # 如果失败(一般是图片太大)，尝试上传移动端的图片
                if len(page_url) == 0:
                    logging.error("api.upload.t__upload_pic() error: %s, try upload mobile pic" % e)
                    upload_illust = api.upload.t__upload_pic(format="json", pic_type=2, pic=download_illust(illust, mobile=True))
                    page_url.append(upload_illust.data.imgurl)
                else:
                    logging.error("api.upload.t__upload_pic(mutipage=%d) error: %s, break with pics: %s" % (i, e, page_url))
                size_error = True
                break

        if (tag_name != ""):
            content_text = "#%s# [%s] / [%s] illust_id=%s %s" % (tag_name, illust.title, illust.authorName, illust.id, illust.url)
        else:
            content_text = "[%s] / [%s] illust_id=%s %s" % (illust.title, illust.authorName, illust.id, illust.url)
        if size_error:
            content_text += " (mobile size)"

        try:
            tweet = api.post.t__add_pic_url(format="json", content=content_text, pic_url=",".join(page_url), clientip="10.0.0.1")
        except TWeiboError, e:
            logging.error("api.post.t__add_pic_url(%s) error: %s, retry" % (",".join(page_url), e))
            if e.body: logging.error("http body: %s" % e.body)
            time.sleep(1.2)
            tweet = api.post.t__add_pic_url(format="json", content=content_text, pic_url=",".join(page_url), clientip="10.0.0.1")

        logging.debug("send tweet: '%s', pageurl=%s" % (content_text, ",".join(page_url)))

    # 将推送过的图片记录到DB
    illust_db = IllustHelper(source)
    illust_db.InsertOrUpdateIllust(illust)
    illust_db.UpdateIllustTweetId(illust.id, tweet.data.id)

    return illust, tweet

def retweet_top_illust(source="all"):
    """ 转发当前分数最高的图片 """
    illust_db = IllustHelper(source)
    top_illust = illust_db.GetUnpubIllustsRank(limit_num=1)
    if (top_illust):
        return retweet_illust_by_id(top_illust.illust_id, tag_name=TWEET_TAG_NAME, source=source)
    else:
        logging.warn("retweet_top_illust() but no unpub illust!")
        return None, None

def add_db_illust_by_id(illust_id):
    pixiv_api = init_pixiv_api()
    illust_db = IllustHelper("all")

    illust = pixiv_api.get_illust(illust_id)
    exist = illust_db.InsertOrUpdateIllust(illust)
    return exist, illust

def disabel_illust_by_id(illust_id):
    illust_db = IllustHelper("all")
    # 将tweet_id填0表示屏蔽
    return illust_db.UpdateIllustTweetId(illust_id, 0)

def crawl_ranking_to_db(content, mode):
    """ 抓取指定排行榜的作品到DB """
    pixiv_api = init_pixiv_api()
    illust_db = IllustHelper(content)

    crawl_count = 0
    new_count = 0

    # 抓取排行榜直到拉取到的图片point小于RANK_POINT_LIMIT
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

            new_count += illust_db.InsertOrUpdateIllust(image)
            crawl_count += 1

        if (page_limit > 0):
            # 处理完一页的数据，翻页继续拉取
            page += 1
            page_limit -= 1
            logging.info("get next page(%d), page_limit=%d" % (page, page_limit))
        else:
            break       # 退出爬取过程

    return new_count, crawl_count, page

def crawl_ranking_log_to_db(log_date, mode):
    """ 抓取历史排行榜的作品到DB """
    pixiv_api = init_pixiv_api()
    illust_db = IllustHelper("log_%s" % mode)

    crawl_count = 0
    new_count = 0

    # 抓取排行榜直到拉取到的图片point小于RANK_POINT_LIMIT
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

            new_count += illust_db.InsertOrUpdateIllust(image)
            crawl_count += 1

        if (page_limit > 0):
            # 处理完一页的数据，翻页继续拉取
            page += 1
            page_limit -= 1
            logging.info("get next page(%d), page_limit=%d" % (page, page_limit))
        else:
            break       # 退出爬取过程

    return new_count, crawl_count, page
