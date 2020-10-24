#!/usr/bin/python3

import re
import time
import logging
import sqlite3
from datetime import datetime

import response

import werobot
import click
import requests
from werobot.replies import ImageReply, ArticlesReply, Article
from werobot.client import Client


config = {
    "APP_ID": "wxfa3723037aa13b99",
    "APP_SECRET": "b6efade9afe3e24c175ae1c97da1afaf"
}
SQLITE_DB_FILE = "/home/werobot.db"

class DB:
    SQL_CREATE_TABLE = "CREATE TABLE IF NOT EXISTS SUBSCRIBE (ID INTEGER PRIMARY KEY AUTOINCREMENT,OPENID CHAR(28) NOT NULL,ACTION_TYPE TEXT NOT NULL, TIME TEXT NOT NULL);"
    SQL_INSERT_ONE_DATA = "INSERT INTO SUBSCRIBE(openid, action_type, time) VALUES(?, ?, ?);"
    SQL_QUERY_ONE_DATA = "SELECT * FROM SUBSCRIBE WHERE openid='{}' AND action_type='{}'"
    SQL_DEL_ONE_DATA = "DELETE FROM SUBSCRIBE where openid ='{}'"
    SQL_GET_BLACKLIST = "SELECT * FROM SUBSCRIBE WHERE action_type='unsubscribe' AND time='{}'"

    def __init__(self):
        self.conn = sqlite3.connect(SQLITE_DB_FILE)
        self.cursor = self.conn.cursor()
        self.create_db_table()

    def create_db_table(self):
        self.conn.execute(self.SQL_CREATE_TABLE)

    def insert(self, user_id, action_type, unsubscribe_time):
        self.conn.execute(self.SQL_INSERT_ONE_DATA, (user_id, action_type, unsubscribe_time))
        self.conn.commit()

    def query_user_by_openid(self, openid, action_type):
        return self.cursor.execute(self.SQL_QUERY_ONE_DATA.format(openid, action_type)).fetchall()

    def delete_by_openid(self, openid):
        self.cursor.execute(self.SQL_DEL_ONE_DATA.format(openid))

    def get_all_blacklist(self):
        return self.cursor.execute(self.SQL_GET_BLACKLIST.format(datetime.now().strftime("%Y-%m-%d"))).fetchall()

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
csver = get_writer("/var/log/keyword_response.csv")
robot = werobot.WeRoBot(token='iswbm', logger=LOG)
client = Client(config)
db = DB()

def get_all_image_items():
    page_count = round(client.get_media_count()/20)
    offset_list = map(lambda x: x * 20, range(page_count))
    for offset in offset_list:
        all_items_json = client.get_media_list(media_type="image", offset=offset, count=20)


def upload_image_media(image_path):
    response = client.upload_permanent_media(media_type="image", media_file=open(image_path, "rb"))
    # 存放数据库
    return response

def is_in_black_list(user_id):
    if db.query_user_by_openid(user_id, "unsubscribe"):
        return True


def save_data(nickname, type, keyword=""):
    if type == "回复":
        LOG.info(nickname + " 正在查询 '{}'".format(keyword))
    elif type == "关注":
        LOG.info(nickname + " 刚刚关注了你!")
    elif type == "取关":
        LOG.info(nickname + " 刚刚取关了你!")
    csver.write("{},{},{},{}\n".format(nickname, type, keyword,datetime.now().strftime("%Y-%m-%d")));csver.flush()

@robot.subscribe
def subscribe(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "关注")
    db.insert(user_info["openid"],"subscribe", datetime.now().strftime("%Y-%m-%d"))
    client.send_text_message(message.source, content=response.welcome.format(user_info["nickname"]))
    # client.send_image_message(message.source, media_id="DRoZL-mq_4ZH0KQ3CR5NuOxT5jau_9PHD3EWzb4t8ls")

@robot.unsubscribe
def unsubscribe(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["openid"], "取关")
    db.insert(user_info["openid"], "unsubscribe", datetime.now().strftime("%Y-%m-%d"))


@robot.filter('暗号')
def subscribe(message):
    user_info = client.get_user_info(message.source)
    if is_in_black_list(user_info["openid"]):
        return response.in_black_list
    reply = ImageReply(message=message, media_id="DRoZL-mq_4ZH0KQ3CR5NuOxT5jau_9PHD3EWzb4t8ls")
    return reply

@robot.filter('vip', 'VIP', '1024', 'more')
def get_vip_code(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "回复", message.content)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.in_black_list
    
    return response.vip

@robot.filter('blog', 'BLOG')
def get_blog(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "回复", message.content)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.in_black_list
    
    reply = ArticlesReply(message=message)
    article = Article(
        title="王炳明の博客",
        description="明哥的个人网站",
        img="https://mmbiz.qpic.cn/mmbiz_jpg/UFM3uMlAXxMehvNJYJ5uwlE1n2rfwbUkHl4MXaBUJO8xflmdLmNShqK9iaMQaLeqbpLbicGHe5V8MyibmhZ9lqbkA/0?wx_fmt=jpeg",
        url="https://iswbm.com"
    )
    reply.add_article(article)
    client.send_text_message(message.source, content=response.blog)
    return reply

@robot.filter('解压密码')
def get_unzip_passwd(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "回复", message.content)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.in_black_list
    
    return response.unzip


@robot.filter('pdf', 'PDF', "黑魔法", '666')
def get_all_pdf(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "回复", message.content)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.in_black_list
    
    return response.pdf

@robot.filter('1012')
def get_pycharm_pdf(message):
    '''
    # 1012: Python猫
    '''
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "回复", message.content)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.in_black_list
    
    return response.pycharm_pdf

@robot.filter("m")
def get_index(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "回复", message.content)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.in_black_list
    
    reply = ArticlesReply(message=message)
    article = Article(
        title="三年的 Python 精华文章汇总",
        description="专属于「{}」的干货目录".format(user_info["nickname"]),
        img="https://mmbiz.qpic.cn/mmbiz_jpg/UFM3uMlAXxMehvNJYJ5uwlE1n2rfwbUkHl4MXaBUJO8xflmdLmNShqK9iaMQaLeqbpLbicGHe5V8MyibmhZ9lqbkA/0?wx_fmt=jpeg",
        # url="https://t.1yb.co/69Kw"
        url="https://github.com/iswbm/python-guide"
    )
    reply.add_article(article)
    return reply

@robot.filter('pycharm')
def get_pycharm_exe(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "回复", message.content)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.in_black_list
    
    return response.pycharm


@robot.filter(re.compile(".*?快捷键.*?"))
def get_pycharm_exe(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "回复", message.content)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.pycharm_keymap

    return response.pycharm

def calc_rate_of_old_iron(subscribe_time, now_time):
    start_time_int = int(time.mktime(datetime.strptime("2019-11-1", "%Y-%m-%d").timetuple()))
    now_time_int = int(time.mktime(now_time.timetuple()))
    subscribe_time_int = int(time.mktime(subscribe_time.timetuple()))
    rate_of_old_iron = (now_time_int - subscribe_time_int) / (now_time_int - start_time_int)
    return rate_of_old_iron

@robot.filter('老铁指数')
def get_user_info(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "回复", message.content)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.in_black_list
    
    subscribe_time = datetime.fromtimestamp(user_info["subscribe_time"])
    now_time = datetime.now()
    subscribe_time_str = subscribe_time.strftime("%Y-%m-%d %H:%M:%S")
    days = (now_time - subscribe_time).days

    rate_of_old_iron = calc_rate_of_old_iron(subscribe_time, now_time)
    content = "昵称: {} \n关注时间: {} \n关注天数: {}\n老铁指数: {:.2%}".format(user_info["nickname"],subscribe_time_str, days,rate_of_old_iron)
    LOG.info("老铁指数查询： \n" + content)
    return content

@robot.filter(re.compile("移除 .*?"))
def remove_from_blacklist(message):
    msg_list = message.content.split(" ")
    if len(msg_list) < 2 or len(msg_list[1]) != 28:
        return "格式(移除 openid)输入有误，请重新输入。"

    LOG.info("准备将 {} 移除黑名单")
    db.delete_by_openid(msg_list[1])
    LOG.info("成功将 {} 移除黑名单")

@robot.filter("黑名单")
def get_blacklist(message):
    blacklist = []
    all_list = db.get_all_blacklist()
    LOG.info(all_list)
    for line in all_list:
        blacklist.append(line[1])

    if blacklist:
        return '\n'.join(blacklist)
    else:
        return "今日暂无黑名单"

@robot.filter(re.compile("单推 .*?"))
def get_single_recommend_info(message):
    import pandas as pd

    # 解决因为中文导致的打印不对齐
    pd.set_option('display.unicode.ambiguous_as_wide', True)
    pd.set_option('display.unicode.east_asian_width', True)

    msg_list = message.content.split(" ")
    if len(msg_list) < 2:
        return "格式输入有误，请重新输入。\n\n比如输入：\n单推 1012  -> 查询 1012 引流人数"

    keyword = msg_list[1]
    all_df = pd.read_csv('/var/log/keyword_response.csv')
    new_df = all_df[(all_df.keyword == keyword)]
    result = str(new_df.groupby("date")["date"].count())

    return result

@robot.filter("dball")
def get_dball(message):
    user_info = client.get_user_info(message.source)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.in_black_list

    return "链接:https://pan.baidu.com/s/1fs1HabmaqezaLxLbHCcqYQ  \n密码:v1mu"

@robot.text
def not_found(message):
    user_info = client.get_user_info(message.source)
    save_data(user_info["nickname"], "回复", message.content)
    if is_in_black_list(user_info["openid"]):
        LOG.info("{} 回复 {} 想获取资料，但之前取关过公众号，现在已经加入黑名单。".format(user_info["nickname"], message.content))
        return response.in_black_list
    
    client.send_text_message(message.source, content=f"不好意思，没有 「{message.content}」 这个关键词，你的「暗号」可能输入有误 或者 已失效。\n\n请按如下暗号进行回复")
    client.send_image_message(message.source, media_id="DRoZL-mq_4ZH0KQ3CR5NuOxT5jau_9PHD3EWzb4t8ls")

@robot.key_click("signal")
def wechat(message):
    reply = ImageReply(message=message, media_id=response.signal_media_id)
    return reply

@robot.key_click("wechat")
def wechat(message):
    reply = ImageReply(message=message, media_id=response.wechat_media_id)
    return reply

def get_qr_code(source_name):
    LOG.info(f"请求创建来源是 {source_name} 的永久性二维码: ")
    access_token = client.grant_token()
    url = "https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token=" + access_token
    data = {"action_name": "QR_LIMIT_SCENE", "action_info": {"scene": {"scene_str": source_name}}}
    response = requests.post(url, data=data)
    if "ticket" not in response.json():
        print("永久性二维码创建失败，需要你是一个认证过的服务号")
        LOG.error("永久性二维码创建失败，需要你是一个认证过的服务号")
    else:
        LOG.info("创建了永久性二维码: " + response.json())
        print(response.json())


def create_memu():
    client.create_menu({
        "button": [
            {
                "name": "专辑",
                "sub_button": [
                    {
                        "type": "view",
                        "name": "玩转PyCharm",
                        "url": response.pycharm_album
                    },
                    {
                        "type": "view",
                        "name": "炫技Python",
                        "url": response.show_album
                    },
                    {
                        "type": "view",
                        "name": "魔法Python",
                        "url": response.magic_album
                    },
                    {
                        "type": "view",
                        "name": "网络知识",
                        "url": response.network_album
                    },
                    {
                        "type": "view",
                        "name": "原创爆文",
                        "url": response.origin_album
                    },
                ]
            },
            {
                "name": "指路",
                "sub_button": [
                    {
                        "type": "view",
                        "name": "暗号",
                        "url": "https://t.1yb.co/7b2A"
                    },
                    {
                        "type": "view",
                        "name": "投稿",
                        "url": "https://t.1yb.co/71U5"
                    },
                    {
                        "type": "view",
                        "name": "目录",
                        "url": "https://github.com/iswbm/python-guide"
                    },
                ]
            },
            {
                "name": "撩我",
                "sub_button": [
                    {
                        "type": "click",
                        "name": "商务合作",
                        "key": "wechat"
                    },
                    {
                        "type": "click",
                        "name": "技术交流",
                        "key": "wechat"
                    }
                ]
            }
        ]})

def delete_menu():
    client.delete_menu()

@click.group()
def handle():
    pass

@handle.command()
def deamon():
    robot.config['HOST'] = '0.0.0.0'
    robot.config['PORT'] = 8080
    create_memu()
    robot.run()

@handle.command()
@click.argument('source', type=click.STRING)
def qrcode(source):
    get_qr_code(source)

@handle.command()
@click.argument('field', type=click.STRING)
@click.argument("date", default=datetime.now().strftime("%Y-%m-%d"))
def analyze(field, date):
    import pandas as pd

    # 解决因为中文导致的打印不对齐
    pd.set_option('display.unicode.ambiguous_as_wide', True)
    pd.set_option('display.unicode.east_asian_width', True)

    all_df = pd.read_csv('/var/log/keyword_response.csv')
    new_df = all_df[(all_df.date == date)]
    print(new_df.groupby(field)[field].count().sort_values(ascending=False))


if __name__ == '__main__':
    handle()