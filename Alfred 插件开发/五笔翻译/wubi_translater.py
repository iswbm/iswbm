# -*- coding:utf-8 -*-
import os
import sys

from workflow import Workflow


def is_chinese(uchar):
    # 判断一个unicode是否是汉字
    if uchar >= u'\u4e00' and uchar <= u'\u9fa5':
        return True
    else:
        return False

def send_feedback(func):
    def deco(*args, **kw):
        func(*args, **kw)
        wf.send_feedback()
    return deco

def wubi(keyword):
    cmd = "/Users/MING/.virtualenvs/Py3.6/bin/python -c \"from pywubi import wubi;print(wubi('{}'))\"".format(keyword.encode("utf-8"))
    result = os.popen(cmd).read().strip()
    return eval(result)[0]

@send_feedback
def main(wf):
    args = wf.args

    if len(args) ==0:
        wf.add_item(title="请开始输入...".decode("utf-8"), subtitle="未输入字符".decode("utf-8"))
        return

    keyword = args[0]

    if not is_chinese(keyword):
        wf.add_item(title="请输入中文...".decode("utf-8"), subtitle="输入有误".decode("utf-8"))
        return

    wf.add_item(title=wubi(keyword), subtitle="完成查询".decode("utf-8"))


if __name__ == '__main__':
    wf = Workflow()
    sys.exit(wf.run(main))