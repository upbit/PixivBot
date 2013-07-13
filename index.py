# -*- coding: utf-8 -*-

import os
import sys
import time
import string
import logging
from datetime import datetime, date, timedelta

### 
from config import *
from api_wrap import *
from db_util import *

import webapp2
import jinja2
JINJA_ENVIRONMENT = jinja2.Environment(autoescape=True, extensions=['jinja2.ext.autoescape'],
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

# default utf8
reload(sys)
sys.setdefaultencoding('utf8')

logging.getLogger().setLevel(logging.INFO)

# jinja2 template tests function
def valid_tweetid(tweet_id):
    if (tweet_id != None) and (tweet_id != "0"):
        return True
    else:
        return False

JINJA_ENVIRONMENT.tests["valid_tweetid"] = valid_tweetid


###
###  RequestHandler define
###
# /
class MainPage(webapp2.RequestHandler):
  def get(self):
    self.redirect("/ranking")

# /ranking - 显示本地榜单
class ShowLocalRanking(webapp2.RequestHandler):
  def get(self):
    try:
        if (self.request.get('mode') != ""):
            rank_mode = self.request.get('mode')
        else:
            rank_mode = "unpub"
        if (self.request.get('page') != ''):
            page = string.atoi(self.request.get('page'))
        else:
            page = 0
        if (page < 0): page = 0
    except ValueError, e:
        logging.error("ValueError: %s" % (e))
        self.response.out.write('Invalid Input: %s' % e)
        return

    illust_db = IllustHelper("all")
    if (rank_mode == "unpub"):
        rank_list = illust_db.GetUnpubIllustsRank(order_by="point", offset=page*30, limit_num=30)
        template_values = { 'ranking': rank_list, 'ranking_uri': "ranking?", 'page': page }
    else:       # 显示所有发表过的内容
        rank_list = illust_db.GetLocalIllustsRank(order_by="point", offset=page*30, limit_num=30)
        template_values = { 'ranking': rank_list, 'ranking_uri': "ranking?mode=all&", 'page': page }

    template = JINJA_ENVIRONMENT.get_template('templates/local_ranking.html')
    self.response.out.write(template.render(template_values))

# /add_illust - 增加指定作品到DB
class AddIllustToDb(webapp2.RequestHandler):
  def get(self):
    try:
        if (self.request.get('id') != ""):
            illust_id = self.request.get('id')
        else:
            logging.warn("illust_id missing")
            return
    except ValueError, e:
        logging.error("ValueError: %s" % (e))
        self.response.out.write('Invalid Input: %s' % e)
        return

    exist, illust = add_db_illust_by_id(illust_id)
    self.response.out.write("[NEW:%d] illust: %s" % (exist, illust))

# /retweet_illust - 转发指定图片
class RetweetIllustById(webapp2.RequestHandler):
  def get(self):
    try:
        if (self.request.get('source') != ""):
            source = self.request.get('source')
        else:
            source = "all"
        if (self.request.get('illust_id') != ""):
            illust_id = string.atoi(self.request.get('illust_id'))
            logging.info("RetweetIllustById(): illust_id=%d" % (illust_id))
        else:
            logging.warn("illust_id missing")
            return
    except ValueError, e:
        logging.error("ValueError: %s" % (e))
        self.response.out.write('Invalid Input: %s' % e)
        return

    illust, tweet = retweet_illust_by_id(illust_id, tag_name=TWEET_TAG_NAME, source=source)
    self.response.out.write("retweet success! <a href='http://t.qq.com/p/t/%s'>ID=%s</a>" % (tweet.data.id, tweet.data.id))

# /disable_illust - 屏蔽一张图片
class DisableIllustById(webapp2.RequestHandler):
  def get(self):
    try:
        if (self.request.get('illust_id') != ""):
            illust_id = string.atoi(self.request.get('illust_id'))
            logging.info("DisableIllustById(): illust_id=%d" % (illust_id))
        else:
            logging.warn("illust_id missing" % (e))
            return
    except ValueError, e:
        logging.error("ValueError: %s" % (e))
        self.response.out.write('Invalid Input: %s' % e)
        return

    disabel_illust_by_id(illust_id)
    self.response.out.write("disable illust_id=%d success." % (illust_id))

# /crawl_ranking
class CrawlRankingToDb(webapp2.RequestHandler):
  def get(self):
    try:
        if (self.request.get('content') in ["all", "male", "female", "original"]):
            content = self.request.get('content')
        else:
            content = "all"
        if (self.request.get('mode') in ['day', 'week', 'month']):
            mode = self.request.get('mode')
        else:
            mode = "day"
    except ValueError, e:
        self.response.out.write('Invalid Input: %s' % e)
        return

    new_count, crawl_count, page = crawl_ranking_to_db(content, mode)
    logging.debug("CrawlRankingToDb(): get %d/%d illusts (%d pages) from ranking(%s)" % (new_count, crawl_count, page, content))
    self.response.out.write("%d/%d %d" % (new_count, crawl_count, page))

# /crawl_ranking_log
class CrawlRankingLogToDb(webapp2.RequestHandler):
  def get(self):
    try:
        if (self.request.get('mode') in ["daily", "weekly", "monthly", "male", "female"]):
            mode = self.request.get('mode')
        else:
            mode = "daily"
        if (self.request.get('year') != ''):
            year = string.atoi(self.request.get('year'))
        else:
            year = date.today().year
        if (self.request.get('month') != ''):
            month = string.atoi(self.request.get('month'))
        else:
            month = date.today().month
        if (self.request.get('day') != ''):
            day = string.atoi(self.request.get('day'))
        else:
            day = date.today().day
    except ValueError, e:
        self.response.out.write('Invalid Input: %s' % e)
        return

    log_date = date(year, month, day)
    new_count, crawl_count, page = crawl_ranking_log_to_db(log_date, mode)
    logging.debug("CrawlRankingLogToDb(): get %d/%d illusts (%d pages) from ranking_log(%s, mode=%s)" % (new_count, crawl_count, page, log_date, mode))
    self.response.out.write("%d/%d %d" % (new_count, crawl_count, page))

# KEY_CRONJOB - 定时任务入口，触发爬取和发表
class CronJobMain(webapp2.RequestHandler):
  def get(self):
    AccessFromCronJob = False
    headers = self.request.headers.items()
    for key, value in headers:
        if (key == 'X-Appengine-Cron') and (value == 'true'):
            AccessFromCronJob = True
            break

    # 如果不是CronJob来源的请求，记录日志并放弃操作
    if (not AccessFromCronJob):
        logging.warn('CronJobMain() access denied!')
        return

    # 开始定时任务处理
    now_date = datetime.utcnow() + timedelta(hours=+8)
    ts_hour = now_date.time().hour
    ts_min = now_date.time().minute / 10

    # 8:00 ~ 23:00 是工作时间，不满足工作时间的直接退出
    if (ts_hour < 8):
        return
    elif (ts_hour == 23) and (ts_min != 0):         # 不是23:00那次直接忽略
        return

    # 每半小时，推送一张评分最高的图片
    if ts_min in [0, 3]:
        illust, tweet = retweet_top_illust()
        logging.info("retweet illust_id=%d [%s] success, tweet_id=%s" % (illust.id, illust.title, tweet.data.id))


# KEY_SPIDER - 爬取Pixiv日榜数据
class RunSpiderDaily(webapp2.RequestHandler):
  def get(self):
    AccessFromCronJob = False
    headers = self.request.headers.items()
    for key, value in headers:
        if (key == 'X-Appengine-Cron') and (value == 'true'):
            AccessFromCronJob = True
            break

    # 如果不是CronJob来源的请求，记录日志并放弃操作
    if (not AccessFromCronJob):
        logging.warn('RunSpiderDaily() access denied!')
        return

    new_count, crawl_count, page = crawl_ranking_to_db("all", "day")
    logging.info("crawl_ranking_to_db() success! get %d/%d (%d pages) illusts" % (new_count, crawl_count, page))


app = webapp2.WSGIApplication([('/', MainPage),
                                ('/ranking', ShowLocalRanking),
                                ('/add_illust', AddIllustToDb),
                                ('/retweet_illust', RetweetIllustById),
                                ('/disable_illust', DisableIllustById),
                                ('/crawl_ranking', CrawlRankingToDb),
                                ('/crawl_ranking_log', CrawlRankingLogToDb),
                                (KEY_CRONJOB, CronJobMain),
                                (KEY_SPIDER, RunSpiderDaily),
                               ], debug=True)
