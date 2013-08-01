# -*- coding: utf-8 -*-

import os
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(autoescape=True, extensions=['jinja2.ext.autoescape'],
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


# jinja2 template tests function
def valid_tweetid(tweet_id):
    if (tweet_id != None) and (tweet_id != "0"):
        return True
    else:
        return False

# jinja2 bot_configs filters function
def check_bot_configs(configs):
    if not configs:
        return []

    result = []
    if configs.enable_config == 0:
        result.append("[ERROR] enable_config: 未生效")
    else:
        result.append("[OK] enable_config: %d" % configs.enable_config)

    try:
        result.append("[OK] oauth2_appkey: %d" % int(configs.oauth2_appkey))
    except ValueError:
        result.append("[ERROR] oauth2_appkey: appkey包含非法字符")
    if len(configs.oauth2_appsecert) != 32:
        result.append("[ERROR] oauth2_appsecert: 长度错误")
    else:
        result.append("[OK] oauth2_appsecert: (已隐去)")
    result.append("[--] oauth2_callbackurl: %s" % configs.oauth2_callbackurl)
    if len(configs.oauth2_accesstoken) != 32:
        result.append("[ERROR] oauth2_accesstoken: 长度错误")
    else:
        result.append("[OK] oauth2_accesstoken: (已隐去)")
    if len(configs.oauth2_openid) != 32:
        result.append("[ERROR] oauth2_openid: 长度错误")
    else:
        result.append("[OK] oauth2_openid: (已隐去)")

    if len(configs.pixiv_user) < 4:
        result.append("[ERROR] pixiv_user: 长度错误")
    else:
        result.append("[OK] pixiv_user: %s" % configs.pixiv_user)
    if len(configs.pixiv_pass) < 4:
        result.append("[ERROR] pixiv_pass: 长度错误")
    else:
        result.append("[OK] pixiv_pass: (已隐去)")

    if (configs.rank_point_limit < 100) or (configs.rank_point_limit > 50000):
        result.append("[ERROR] rank_point_limit: %s (超出推荐范围, 100-50000)" % configs.rank_point_limit)
    else:
        result.append("[OK] rank_point_limit: %s" % configs.rank_point_limit)
    if (configs.rank_max_page <= 0) or (configs.rank_max_page > 10):
        result.append("[ERROR] rank_max_page: %s (超出推荐范围, 1-10)" % configs.rank_max_page)
    else:
        result.append("[OK] rank_max_page: %s" % configs.rank_max_page)
    result.append("[--] tweet_tag_name: #%s#" % configs.tweet_tag_name)

    if configs.enable_cronjob == 0:
        result.append("[ERROR] enable_cronjob: CronJob被禁用")
    else:
        result.append("[OK] enable_cronjob: %d" % configs.enable_cronjob)
    if configs.enable_crawljobs == 0:
        result.append("[ERROR] enable_crawljobs: 自动抓取被禁用")
    else:
        result.append("[OK] enable_crawljobs: %d" % configs.enable_crawljobs)

    return result

def checkbox(bool_val):
    if bool_val:
        return "checked"
    else:
        return ""

JINJA_ENVIRONMENT.tests["valid_tweetid"] = valid_tweetid
JINJA_ENVIRONMENT.filters["check_bot_configs"] = check_bot_configs
JINJA_ENVIRONMENT.filters["checkbox"] = checkbox
