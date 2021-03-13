# coding: utf-8

# 基于 Python 2 编写

import os
import sys
import shutil
import commands

def encrypt_file(file):
    filename, ext = os.path.splitext(file)
    dir_name = filename
    os.mkdir(dir_name)
    shutil.copy(src=file, dst=dir_name)
    os.chdir(dir_name)
    zip_cmd = '/usr/bin/zip -P "iswbm.com" "{}.zip" "{}"'.format(filename, file)
    zip_cmd_no_pass = '/usr/bin/zip -r "{}.zip" "{}"'.format(dir_name, dir_name)
    wget_cmd = '/usr/local/bin/wget -q http://image.iswbm.com/get_zip_pass_02.png'

    commands.getstatusoutput(zip_cmd)
    commands.getstatusoutput(wget_cmd)
    os.rename("get_zip_pass_02.png", "解压密码，看这里.png")
    os.remove(file)

    os.chdir("..")
    commands.getstatusoutput(zip_cmd_no_pass)
    shutil.rmtree(dir_name)
    print("Success!")

for file in sys.stdin:
    dir,file = os.path.split(file.strip())
    os.chdir(dir)
    if os.path.isfile(file):
        encrypt_file(file)
    else:
        print("Can not zip directionary({})!".format(file))