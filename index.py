# -*- coding: utf-8 -*-

import sys
import time
import string
import logging
from datetime import datetime, date, timedelta

import webapp2
from jinja2_func import *
from db_util import *
from api_wrap import *

###
# 定时任务入口，可以修改成任意难以猜到的字符串
KEY_CRONJOB = '/KEY_aHR0cHM6Ly9naXRodWIuY29tL3VwYml0L1BpeGl2Qm90'
KEY_SPIDER = '/DAILY_VUdsNGFYWlRjR2xrWlhKZlMwVlpYMU5RU1VSRlVn'

# default utf8
reload(sys)
sys.setdefaultencoding('utf8')

logging.getLogger().setLevel(logging.INFO)

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
        rank_mode = self.request.get('mode', default_value="unpub")
        page = string.atoi(self.request.get('page', "0"))
        if (page < 0): page = 0
    except ValueError, e:
        logging.error("ValueError: %s" % (e))
        self.response.out.write('Invalid Input: %s' % e)
        return

    illust_helper = IllustHelper("all")
    if (rank_mode == "unpub"):
        illust_list = illust_helper.get_illusts_by_rank(only_unpub=True, order_by="point", offset=page*50, limit_num=50)
        template_values = { 'illust_list': illust_list, 'illust_uri': "ranking?", 'page': page }
    else:       # 显示所有发表过的内容
        illust_list = illust_helper.get_illusts_by_rank(only_unpub=False, order_by="point", offset=page*50, limit_num=50)
        template_values = { 'illust_list': illust_list, 'illust_uri': "ranking?mode=all&", 'page': page }

    template = JINJA_ENVIRONMENT.get_template('templates/illust_list.html')
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
        source = self.request.get('source', default_value="all")
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

    bot_configs = BotSetup.getConfigs()
    illust, tweet = retweet_illust_by_id(illust_id, tag_name=bot_configs.tweet_tag_name, source=source)
    if tweet:
        self.response.out.write("retweet success! <a href='http://t.qq.com/p/t/%s'>ID=%s</a>" % (tweet.data.id, tweet.data.id))
        logging.info("retweet illust_id=%d [%s] success, tweet_id=%s" % (illust.id, illust.title, tweet.data.id))

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
        content = self.request.get('content', default_value="all")
        if not (self.request.get('content') in ["all", "male", "female", "original"]):
            content = "all"
        mode = self.request.get('mode', default_value="day")
        if not (self.request.get('mode') in ['day', 'week', 'month']):
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
        mode = self.request.get('mode', default_value="daily")
        if not (self.request.get('mode') in ["daily", "weekly", "monthly", "male", "female"]):
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
    #if (not AccessFromCronJob):
    #    logging.warn('CronJobMain() access denied!')
    #    return

    # 检查配置，看是否启用定时任务
    bot_configs = BotSetup.getConfigs()
    if not bot_configs:
        logging.warn("PixivBot is not installed! To deploy, please follow the Configuration Guide.")
        return
    if not bot_configs.enable_cronjob:
        logging.info("CronJob disabled in BotSetup.enable_cronjob")
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

    # 满足要求，推送一张评分最高的图片
    if ts_min in [0, 2, 4]:
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
    #if (not AccessFromCronJob):
    #    logging.warn('RunSpiderDaily() access denied!')
    #    return

    # 检查配置，看是否启用抓取
    bot_configs = BotSetup.getConfigs()
    if not bot_configs:
        logging.warn("PixivBot is not installed! To deploy, please follow the Configuration Guide.")
        return
    if not bot_configs.enable_crawljobs:
        logging.info("CrawlJobs disabled in BotSetup.enable_crawljobs")
        return

    new_count, crawl_count, page = crawl_ranking_to_db("all", "day")
    logging.info("crawl_ranking_to_db() success! get %d/%d (%d pages) illusts" % (new_count, crawl_count, page))

# /admin/setup - 初始化Bot并生成 BotSetup 配置项
class SetupBotConfigs(webapp2.RequestHandler):
  def get(self):
    bot_configs = BotSetup.getConfigs()
    if not bot_configs:
        bot_configs = BotSetup(enable_config = 1,
                oauth2_appkey = "801376349",
                oauth2_appsecert = "c057534d14cba920579f2d54005e0c06",
                oauth2_callbackurl = "https://github.com",
                tweet_tag_name = "Pixiv日榜",
                enable_cronjob = 0,
                enable_crawljobs = 0
            )
        bot_configs.put()

    template_values = { 'bot_configs': bot_configs }
    template = JINJA_ENVIRONMENT.get_template('templates/setup.html')
    self.response.out.write(template.render(template_values))

  def post(self):
    try:
        bot_configs = BotSetup.getConfigs()

        check_enable_config = self.request.get('enable_config', default_value="off")
        if (check_enable_config == "on"):
            bot_configs.enable_config = 1
        else:
            bot_configs.enable_config = 0

        bot_configs.oauth2_appkey = self.request.get('oauth2_appkey', default_value="")
        bot_configs.oauth2_appsecert = self.request.get('oauth2_appsecert', default_value="")
        bot_configs.oauth2_callbackurl = self.request.get('oauth2_callbackurl', default_value="")
        bot_configs.oauth2_accesstoken = self.request.get('oauth2_accesstoken', default_value="")
        bot_configs.oauth2_openid = self.request.get('oauth2_openid', default_value="")

        bot_configs.pixiv_user = self.request.get('pixiv_user', default_value="")
        bot_configs.pixiv_pass = self.request.get('pixiv_pass', default_value="")

        bot_configs.rank_point_limit = int(self.request.get('rank_point_limit', default_value="5000"))
        bot_configs.rank_max_page = int(self.request.get('rank_max_page', default_value="10"))
        bot_configs.tweet_tag_name = self.request.get('tweet_tag_name', default_value="")

        check_enable_cronjob = self.request.get('enable_cronjob', default_value="off")
        if (check_enable_cronjob == "on"):
            bot_configs.enable_cronjob = 1
        else:
            bot_configs.enable_cronjob = 0
        check_enable_crawljobs = self.request.get('enable_crawljobs', default_value="off")
        if (check_enable_crawljobs == "on"):
            bot_configs.enable_crawljobs = 1
        else:
            bot_configs.enable_crawljobs = 0

        bot_configs.put()

    except Exception, e:
        logging.error("get bot_configs setting error: %s" % (e))
        return

    template_values = { 'bot_configs': bot_configs }
    template = JINJA_ENVIRONMENT.get_template('templates/setup.html')
    self.response.out.write(template.render(template_values))


app = webapp2.WSGIApplication([('/', MainPage),
                                ('/ranking', ShowLocalRanking),
                                ('/add_illust', AddIllustToDb),
                                ('/retweet_illust', RetweetIllustById),
                                ('/disable_illust', DisableIllustById),
                                ('/crawl_ranking', CrawlRankingToDb),
                                ('/crawl_ranking_log', CrawlRankingLogToDb),
                                (KEY_CRONJOB, CronJobMain),
                                (KEY_SPIDER, RunSpiderDaily),
                                ('/admin/setup', SetupBotConfigs),
                               ], debug=True)
