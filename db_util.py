# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from google.appengine.ext import db
from google.appengine.ext import ndb

conv_utf8 = lambda s: unicode(s, 'utf-8')

class BotSetup(ndb.Model):
  enable_config = ndb.IntegerProperty(default=1)

  oauth2_appkey = ndb.StringProperty(default="", indexed=False)
  oauth2_appsecert = ndb.StringProperty(default="", indexed=False)
  oauth2_callbackurl = ndb.StringProperty(default="", indexed=False)
  oauth2_accesstoken = ndb.StringProperty(default="", indexed=False)
  oauth2_openid = ndb.StringProperty(default="", indexed=False)

  pixiv_user = ndb.StringProperty(default="", indexed=False)
  pixiv_pass = ndb.StringProperty(default="", indexed=False)

  rank_point_limit = ndb.IntegerProperty(default=5000, indexed=False)
  rank_max_page = ndb.IntegerProperty(default=10, indexed=False)
  tweet_tag_name = ndb.StringProperty(default="Pixiv", indexed=False)

  enable_cronjob = ndb.IntegerProperty(default=1, indexed=False)
  enable_crawljobs = ndb.IntegerProperty(default=1, indexed=False)

  @classmethod
  def getConfigs(cls):
    query = ndb.gql("SELECT * FROM BotSetup WHERE enable_config != 0")
    return query.get()


class IllustModel(ndb.Model):
  """Illust对象, Key为IllustId"""
  author_id = ndb.IntegerProperty(required=True)
  author_name = ndb.StringProperty(required=True, indexed=False)

  title = ndb.StringProperty(required=True)
  thumb_url = ndb.StringProperty(required=True, indexed=False)
  date = ndb.DateTimeProperty()
  source = ndb.StringProperty(required=True)

  feedback = ndb.IntegerProperty()
  point = ndb.IntegerProperty()
  views = ndb.IntegerProperty()

  tweet_id = ndb.StringProperty(default=None)       # 发表后的微博ID

  @classmethod
  def create_key(cls, illust_id):
    """根据illust_id生成key"""
    return ndb.Key(IllustModel, "%s" % illust_id)

  @classmethod
  def get_illust(cls, illust_id):
    return ndb.Key(IllustModel, "%s" % illust_id).get()


class IllustHelper():
    def __init__(self, rank_source="all"):
        self.rank_source = rank_source

    def update_or_insert(self, illust_obj):
        db_illust = IllustModel.get_illust(illust_obj.id)
        if not db_illust:
            # 对应id的作品不存在，创建新的对象
            db_illust = IllustModel(key = IllustModel.create_key(illust_obj.id),
                author_id = illust_obj.authorId,
                author_name = conv_utf8(illust_obj.authorName),
                title = conv_utf8(illust_obj.title),
                thumb_url = illust_obj.thumbURL,
                date = datetime.strptime(illust_obj.date, "%Y-%m-%d %H:%M:%S"),
                source = self.rank_source,
                feedback = illust_obj.feedback,
                point = illust_obj.point,
                views = illust_obj.views
            )
            exist = 0
        else:
            # 已存在作品，更新分值
            db_illust.feedback = illust_obj.feedback
            db_illust.point = illust_obj.point
            db_illust.views = illust_obj.views
            exist = 1
        db_illust.put()
        return exist, db_illust

    def update_illust_tweetid(self, illust_id, tweet_id):
        db_illust = IllustModel.get_illust(illust_id)
        if not db_illust:
            return None
        db_illust.tweet_id = str(tweet_id)
        db_illust.put()
        return db_illust

    def get_illusts_by_rank(self, only_unpub=False, order_by="point", offset=0, limit_num=1):
        if only_unpub:
            query = ndb.gql("SELECT * FROM IllustModel WHERE tweet_id=:1 ORDER BY %s DESC LIMIT %d,%d" % (order_by, offset, limit_num), None)
        else:
            query = ndb.gql("SELECT * FROM IllustModel ORDER BY %s DESC LIMIT %d,%d" % (order_by, offset, limit_num))
        if (limit_num > 1):
            return query.fetch()
        else:
            return query.get()

