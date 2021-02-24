#!/usr/bin/python3

import re
import time
import logging
import threading
from datetime import datetime
from functools import wraps

import werobot
import click
import toml

import pandas as pd
from werobot.replies import ImageReply, ArticlesReply, Article
from werobot.client import Client
from sqlalchemy import Column, Integer, String, Boolean, Date, create_engine, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

cfg_dict = toml.load("/etc/werobot/werobot.toml")
config = cfg_dict["werobot"]["config"]
mysql_config = cfg_dict["mysql"]
str_key_response_mapping = cfg_dict["werobot"]["keyword"]["string"]
re_key_response_mapping = cfg_dict["werobot"]["keyword"]["regex"]
lottery_draw_info = cfg_dict["werobot"]["keyword"]["lottery"]
media_ids = cfg_dict["werobot"]["media"]


lock = threading.Lock()
Base = declarative_base()

class MYSQL:
    def __init__(self):
        mysql_uri = 'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'.format(**mysql_config)
        self.engine = create_engine(mysql_uri)
        DBsession = sessionmaker(bind=self.engine)
        self.session = DBsession()
        self.create_db_table()


    def create_db_table(self):
        Base.metadata.create_all(self.engine, checkfirst=True)

    def add_subscribe(self, user_info):
        openid = user_info["openid"]
        nickname = user_info["nickname"]

        if not self.session.query(User).filter_by(openid=openid).all():
            self.session.add(User(openid=openid, name=nickname))
            self.session.commit()

        subscribe_time = datetime.fromtimestamp(user_info["subscribe_time"])
        self.session.add(Subscribe(userid=openid, action="关注", action_time=subscribe_time))

    def cancel_subscribe(self, openid):
        if not self.session.query(User).filter_by(openid=openid).all():
            self.session.add(User(openid=openid, name="unknown"))
            self.session.commit()
        self.session.query(User).filter_by(openid=openid).update({User.baned: True})
        self.session.add(Subscribe(userid=openid, action="取关"))
        self.session.commit()

    def add_message(self, user_info, message):
        if not self.session.query(User).filter_by(openid=user_info["openid"]).all():
            self.session.add(User(openid=user_info["openid"], name=user_info["nickname"]))
            self.session.commit()
        self.session.add(Message(userid=user_info["openid"], message=message))
        self.session.commit()

    def is_banned(self, openid):
        return self.session.query(User).filter_by(openid=openid, baned=True).all()

    def remove_from_blacklist(self, openid):
        self.session.query(User).filter_by(openid=openid).update({User.baned: False})
        self.session.commit()

    def get_all_blacklist(self):
        return self.session.query(Subscribe).filter_by(action="取关", action_time=datetime.today()).all()

    def recommend_info(self, keyword):
        result = self.session.query(Message.date, func.count(Message.date)).filter_by(message=keyword).group_by("date").all()
        if not result:
            return "该关键词暂无人关注"

        lines = ["关键词: {}".format(keyword)]
        for data in result:
            line = "{} {}".format(data[0].strftime("%Y-%m-%d"), data[1])
            lines.append(line)

        return '\n'.join(lines)


# 自定义的表
class User(Base):
    __tablename__ = 'users'

    # 定义字段
    openid = Column(String(28), primary_key=True)
    name = Column(String(255))
    baned = Column(Boolean, default=False)


class Subscribe(Base):
    __tablename__ = 'subscribe'
    id = Column(Integer, primary_key=True)
    userid = Column(String(28), ForeignKey("users.openid"))
    action = Column(String(10))
    action_time = Column(Date, default=datetime.now())


class Message(Base):
    __tablename__ = 'messages'

    # 定义字段
    id = Column(Integer, primary_key=True)
    userid = Column(String(28), ForeignKey("users.openid"))
    message = Column(String(255))
    date = Column(Date, default=datetime.now)


def get_logger(logpath):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(logpath)
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger

def get_writer(file_path):
    return open(file_path, '+a')

LOG = get_logger("/var/log/werobot.log")
# csver = get_writer("/var/log/keyword_response.csv")
robot = werobot.WeRoBot(token='iswbm', logger=LOG)
client = Client(config)
db = MYSQL()

def upload_image_media(client, image_path):
    print(client.upload_permanent_media(media_type="image", media_file=open(image_path, "rb")))


def save_data_and_check_black_list(dbclient):
    def is_in_black_list(user_id):
        if db.is_banned(user_id):
            return True

    def wrapper(func):
        @wraps(func)
        def deco(*args, **kw):
            message = args[0]
            user_info = client.get_user_info(message.source)
            LOG.info("user_id: {}, user_info: {}".format(message.source, user_info))
            LOG.info("{} 正在查询 '{}'".format(user_info["nickname"], message.content))
            dbclient.add_message(user_info, message.content)
            if is_in_black_list(user_info["openid"]):
                LOG.info(
                    "{} (id: {})回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], user_info["openid"],
                                                                         message.content))
                return cfg_dict["werobot"]["common"]["in_black_list"]
            return func(*args, **kw)
        return deco
    return wrapper


class WerobotBackend:
    def __init__(self, robot, dbclient):
        self.robot = robot
        self.dbclient = dbclient
        self.register_events()
        self.register_keywords()

    def register_events(self):
        def subscribe(message):
            user_info = client.get_user_info(message.source)
            LOG.info("{}({}) 刚刚关注了你".format(user_info["nickname"], user_info["openid"]))
            self.dbclient.add_subscribe(user_info)
            client.send_text_message(message.source,
                                     content=cfg_dict["werobot"]["common"]["welcome"].format(user_info["nickname"]))

        def unsubscribe(message):
            user_info = client.get_user_info(message.source)
            # user_info: {'subscribe': 0, 'openid': 'ojde4wEz4QhPjJjhNApqgP4B8pTE', 'tagid_list': []}
            LOG.info("{} 刚刚取关了你".format(user_info["openid"]))
            self.dbclient.cancel_subscribe(user_info["openid"])

        def communication(message):
            reply = ImageReply(message=message, media_id="mEloyztypmjpHsAx8NnTlyIcOmY2ql-PAdfs8fEJRJY")
            return reply

        def business(message):
            reply = ImageReply(message=message, media_id="mEloyztypmjpHsAx8NnTlz4c8GiuEUxnBULz135LaF0")
            return reply

        self.robot.subscribe(subscribe)
        self.robot.unsubscribe(unsubscribe)
        self.robot.key_click("communication")(communication)
        self.robot.key_click("business")(business)

    def register_keywords(self):
        @save_data_and_check_black_list(dbclient=self.dbclient)
        def str_response(message):
            result = str_key_response_mapping.get(message.content)
            return result

        @save_data_and_check_black_list(dbclient=self.dbclient)
        def re_response(message, session, check_result):
            keyword = check_result.re.pattern.replace(".*?", "")
            return re_key_response_mapping.get(keyword, "回复有误")

        @save_data_and_check_black_list(dbclient=self.dbclient)
        def get_user_info(message):
            user_info = client.get_user_info(message.source)
            subscribe_time = datetime.fromtimestamp(user_info["subscribe_time"])
            now_time = datetime.now()
            subscribe_time_str = subscribe_time.strftime("%Y-%m-%d %H:%M:%S")
            days = (now_time - subscribe_time).days

            rate_of_old_iron = self.calc_rate_of_old_iron(subscribe_time, now_time)
            content = "昵称: {} \n关注时间: {} \n关注天数: {}\n老铁指数: {:.2%}".format(user_info["nickname"], subscribe_time_str,
                                                                          days,
                                                                          rate_of_old_iron)
            LOG.info("老铁指数查询： \n" + content)
            return content

        def get_single_recommend_info(message):
            # 解决因为中文导致的打印不对齐
            pd.set_option('display.unicode.ambiguous_as_wide', True)
            pd.set_option('display.unicode.east_asian_width', True)

            msg_list = message.content.split(" ")
            if len(msg_list) < 2:
                return "格式输入有误，请重新输入。\n\n比如输入：\n单推 1012  -> 查询 1012 引流人数"

            keyword = msg_list[1]
            return self.dbclient.recommend_info(keyword)

        def remove_from_blacklist(message):
            msg_list = message.content.split(" ")
            if len(msg_list) < 2 or len(msg_list[1]) != 28:
                return "格式(移除 openid)输入有误，请重新输入。"

            LOG.info("准备将 {} 移除黑名单".format(msg_list[1]))
            self.dbclient.remove_from_blacklist(msg_list[1])
            LOG.info("成功将 {} 移除黑名单".format(msg_list[1]))
            return "成功将 {} 移除黑名单".format(msg_list[1])

        def get_blacklist(message):
            blacklist = []
            all_list = self.dbclient.get_all_blacklist()
            for obj in all_list:
                blacklist.append(obj.userid)

            if blacklist:
                return '\n'.join(blacklist)
            else:
                return "今日暂无黑名单"


        @save_data_and_check_black_list(dbclient=self.dbclient)
        def get_signal_info(message):
            reply = ImageReply(message=message, media_id=media_ids["signal_media_id"])
            return reply

        @save_data_and_check_black_list(dbclient=self.dbclient)
        def get_blog(message):
            reply = ArticlesReply(message=message)
            article = Article(
                title="王炳明の博客",
                description="明哥的个人网站",
                img="https://mmbiz.qpic.cn/mmbiz_jpg/UFM3uMlAXxMehvNJYJ5uwlE1n2rfwbUkHl4MXaBUJO8xflmdLmNShqK9iaMQaLeqbpLbicGHe5V8MyibmhZ9lqbkA/0?wx_fmt=jpeg",
                url="https://iswbm.com"
            )
            reply.add_article(article)
            client.send_text_message(message.source, content=cfg_dict["werobot"]["common"]["blog"])
            return reply

        @save_data_and_check_black_list(dbclient=self.dbclient)
        def get_index(message):
            user_info = client.get_user_info(message.source)
            reply = ArticlesReply(message=message)
            article = Article(
                title="三年的 Python 精华文章汇总",
                description="专属于「{}」的干货目录".format(user_info["nickname"]),
                img="https://mmbiz.qpic.cn/mmbiz_jpg/UFM3uMlAXxMehvNJYJ5uwlE1n2rfwbUkHl4MXaBUJO8xflmdLmNShqK9iaMQaLeqbpLbicGHe5V8MyibmhZ9lqbkA/0?wx_fmt=jpeg",
                # url="https://t.1yb.co/69Kw"
                url="https://github.com/iswbm/PythonCodingTime"
            )
            reply.add_article(article)
            return reply

        @save_data_and_check_black_list(dbclient=self.dbclient)
        def lottery_draw(message):
            media_id = lottery_draw_info[message.content]["media_id"]
            article_url = lottery_draw_info[message.content]["article_url"]
            remark = lottery_draw_info[message.content]["remark"]
            client.send_image_message(message.source, media_id=media_id)
            client.send_text_message(message.source,
                                     content='参与抽奖之前，请点击这个链接，阅读规则：<a href="{}">送红包规则，千万要看！</a>'.format(article_url))
            return remark

        @save_data_and_check_black_list(dbclient=self.dbclient)
        def not_found(message):
            return "不好意思，没有 「{}」 这个关键词，你的「暗号」可能已经失效, 请联系管理员微信(微信号: hello-wbm)进行获取 。".format(message.content)

        # TODO: 待使用
        @save_data_and_check_black_list(dbclient=self.dbclient)
        def return_single_pic(message):
            reply = ImageReply(message=message, media_id="")
            return reply

        # 精准关键词
        str_keywords = str_key_response_mapping.keys()
        self.robot.filter(*str_keywords)(str_response)

        # 模糊关键词
        for key in re_key_response_mapping.keys():
            self.robot.filter(re.compile(".*?{}.*?".format(key)))(re_response)

        self.robot.filter(re.compile("单推 .*?"))(get_single_recommend_info)
        self.robot.filter(re.compile("移除 .*?"))(remove_from_blacklist)

        # 常用暗号
        self.robot.filter('blog', 'BLOG')(get_blog)
        self.robot.filter('m')(get_index)
        self.robot.filter("黑名单")(get_blacklist)
        self.robot.filter("老铁指数")(get_user_info)
        self.robot.filter("暗号")(get_signal_info)

        # 抽奖专用
        for code in lottery_draw_info.keys():
            self.robot.filter(code)(lottery_draw)

        self.robot.text(not_found)

    @staticmethod
    def calc_rate_of_old_iron(subscribe_time, now_time):
        start_time_int = int(time.mktime(datetime.strptime("2019-11-1", "%Y-%m-%d").timetuple()))
        now_time_int = int(time.mktime(now_time.timetuple()))
        subscribe_time_int = int(time.mktime(subscribe_time.timetuple()))
        rate_of_old_iron = (now_time_int - subscribe_time_int) / (now_time_int - start_time_int)
        return rate_of_old_iron

def migrate_users_data():
    log = get_logger("/var/log/migrate.log")
    next_openid = None
    count = 0
    while True:
        res = client.get_followers(next_openid)
        if res["count"] == 0:
            break

        next_openid = res["next_openid"]

        for openid in res["data"]["openid"]:
            count += 1
            log.info("正在处理 {} 个用户信息: {}".format(count, openid))
            user_info = client.get_user_info(openid)
            db.add_subscribe(user_info)

        log.info("处理完成")



@click.group()
def handle():
    pass

@handle.command()
def deamon():
    robot.config['HOST'] = cfg_dict["werobot"]["host"]
    robot.config['PORT'] = cfg_dict["werobot"]["port"]
    WerobotBackend(robot, dbclient=db)
    client.create_menu(cfg_dict["werobot"]["menu"])  # client.delete_menu()
    robot.run()


@handle.command()
@click.argument('path', type=click.STRING)
def uploadpic(path):
    upload_image_media(client, path)


@handle.command()
@click.argument('field', type=click.STRING)
@click.argument("date", default=datetime.now().strftime("%Y-%m-%d"))
def analyze(field, date):
    # 解决因为中文导致的打印不对齐
    pd.set_option('display.unicode.ambiguous_as_wide', True)
    pd.set_option('display.unicode.east_asian_width', True)

    all_df = pd.read_csv('/var/log/keyword_response.csv')
    new_df = all_df[(all_df.date == date)]
    print(new_df.groupby(field)[field].count().sort_values(ascending=False))


if __name__ == '__main__':
    handle()