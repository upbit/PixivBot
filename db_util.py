# -*- coding: utf-8 -*-

import logging
from google.appengine.ext import db

conv_utf8 = lambda s: unicode(s, 'utf-8')

## cleanup unpub db
#
# from google.appengine.ext import db
# from db_util import *
#
# query = db.GqlQuery("select * from IllustDb where tweet_id=:1", None)
# results = query.fetch(1000)
# db.delete(results)
#

# Illust存储
class IllustDb(db.Model):
    illust_id = db.IntegerProperty()
    author_id = db.IntegerProperty()
    title = db.StringProperty(multiline=False)              # 图片标题
    author_name = db.StringProperty(multiline=False)        # 作者名
    thumb_url = db.LinkProperty()                           # 缩略图URL
    date = db.StringProperty(multiline=False)               # 发表时间

    feedback = db.IntegerProperty()
    point = db.IntegerProperty()
    views = db.IntegerProperty()
    bookmark = db.IntegerProperty()
    recommend = db.IntegerProperty()

    tweet_id = db.StringProperty(multiline=False)           # 发表的消息ID

    source = db.StringProperty()                            # 图片来源
    memo = db.StringProperty(multiline=True)


#
class IllustHelper():
    def __init__(self, rank_source="all"):
        self.rank_source = rank_source

    def _GetIllust(self, illust_id):
        """ 根据id查询illust """
        query = db.GqlQuery("select * from IllustDb where illust_id=:illust_id limit 1", illust_id=illust_id)
        return query.get()

    def SearchAuthorIllusts(self, author_id):
        """ 根据id查询author的所有illust """
        query = db.GqlQuery("select * from IllustDb where author_id=:1", author_id=author_id)
        return query.run()

    def InsertOrUpdateIllust(self, illust_obj):
        """ 插入或更新一个illust的信息 """
        insert_new = 1
        db_illust = self._GetIllust(illust_obj.id)
        if (not db_illust):
            db_illust = IllustDb()
            db_illust.illust_id = illust_obj.id
            db_illust.author_id = illust_obj.authorId
            db_illust.title = conv_utf8(illust_obj.title)
            db_illust.author_name = conv_utf8(illust_obj.authorName)
            db_illust.thumb_url = db.Link(illust_obj.thumbURL)
            db_illust.date = illust_obj.date
            db_illust.feedback = illust_obj.feedback
            db_illust.point = illust_obj.point
            db_illust.views = illust_obj.views
            db_illust.bookmark = 0
            db_illust.recommend = 0
            db_illust.tweet_id = None
            db_illust.source = self.rank_source
        else: # update illust
            if (db_illust.feedback < illust_obj.feedback): db_illust.feedback = illust_obj.feedback
            if (db_illust.point < illust_obj.point): db_illust.point = illust_obj.point
            if (db_illust.views < illust_obj.views): db_illust.views = illust_obj.views
            insert_new = 0
            logging.debug("exist, update illust %d" % (db_illust.illust_id))

        db_illust.put()
        return insert_new

    def UpdateIllustTweetId(self, illust_id, tweet_id):
        """ 更新Illust的微博消息id，tweet_id=0表示屏蔽 """
        db_illust = self._GetIllust(illust_id)
        if (not db_illust):
            logging.warn("UpdateTweetId() but illust_id=%d not found!" % (illust_id))
            return None
        db_illust.tweet_id = str(tweet_id)
        return db_illust.put()

    def GetUnpubIllustsRank(self, order_by="point", offset=0, limit_num=1):
        """ 查询排行前N且未发表的illust """
        query = db.GqlQuery("select * from IllustDb where tweet_id=:1 order by %s desc limit %d,%d" % (order_by, offset, limit_num), None)
        if (limit_num > 1):
            return query.run()
        else:
            return query.get()

    def GetLocalIllustsRank(self, order_by="point", offset=0, limit_num=1):
        """ 查询本地排行榜(包括已推送) """
        query = db.GqlQuery("select * from IllustDb order by %s desc limit %d,%d" % (order_by, offset, limit_num))
        if (limit_num > 1):
            return query.run()
        else:
            return query.get()

