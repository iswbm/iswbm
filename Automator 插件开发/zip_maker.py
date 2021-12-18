# coding: utf-8

# 基于 Python 2 编写

import os
import sys
import shutil
import commands


def encrypt_file():
    # 创建新目录，并移动文件到新目录中
    new_dir_name, ext = os.path.splitext(file_name)
    os.mkdir(new_dir_name)
    shutil.copy(src=file_name, dst=new_dir_name)
    os.chdir(new_dir_name)

    # 加密压缩
    zip_cmd = '/usr/bin/zip -P "iswbm.com" "{}.zip" "{}"'.format(new_dir_name, file_name)
    commands.getstatusoutput(zip_cmd)
    os.remove(file_name)

    # 下载提示图片
    wget_cmd = '/opt/homebrew/bin/wget -q http://image.iswbm.com/get_zip_pass_04.png -O 解压密码，看这里.png'
    commands.getstatusoutput(wget_cmd)

    # 无密压缩
    os.chdir("..")
    zip_cmd_no_pass = '/usr/bin/zip -r "{}-res.zip" "{}"'.format(new_dir_name, new_dir_name)
    commands.getstatusoutput(zip_cmd_no_pass)
    shutil.rmtree(new_dir_name)

    print("Success!")


def encrypt_file_folder():
    os.mkdir("tmp")
    shutil.copytree(src=dir_name, dst="tmp/{}".format(dir_name))
    os.chdir("tmp")

    # 加密压缩
    zip_cmd = '/usr/bin/zip -r -P "iswbm.com" "{}.zip" "{}"'.format(dir_name, dir_name)
    commands.getstatusoutput(zip_cmd)
    shutil.rmtree(dir_name)

    # 下载提示图片
    wget_cmd = '/opt/homebrew/bin/wget -q http://image.iswbm.com/get_zip_pass_04.png -O 解压密码，看这里.png'
    commands.getstatusoutput(wget_cmd)

    # 无密压缩
    zip_cmd_no_pass = '/usr/bin/zip -r "{}-res.zip" ./'.format(dir_name, dir_name)
    commands.getstatusoutput(zip_cmd_no_pass)
    os.remove("解压密码，看这里.png")

    # 移动压缩包到外面
    shutil.copyfile("{}-res.zip".format(dir_name), "../{}-res.zip".format(dir_name))
    os.chdir("..")
    shutil.rmtree("tmp")
    print("Success!")


for target_path in sys.stdin:
    dir_path, file_or_dir_name = os.path.split(target_path.strip())
    os.chdir(dir_path)
    if os.path.isfile(target_path.strip()):
        file_name = file_or_dir_name
        encrypt_file()
    else:
        dir_name = file_or_dir_name
        encrypt_file_folder()
