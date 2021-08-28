# coding: utf-8

# 基于 Python 2 编写

import os
import sys
import shutil
import commands

zip_pass_png_name = "get_zip_pass_01.png"

def encrypt_file(file):
    filename, ext = os.path.splitext(file)
    dir_name = filename
    os.mkdir(dir_name)
    shutil.copy(src=file, dst=dir_name)
    os.chdir(dir_name)
    zip_cmd = '/usr/bin/zip -P "iswbm.com" "{}.zip" "{}"'.format(filename, file)
    zip_cmd_no_pass = '/usr/bin/zip -r "{}.zip" "{}"'.format(dir_name, dir_name)
    wget_cmd = '/usr/local/bin/wget -q http://image.iswbm.com/' + zip_pass_png_name

    commands.getstatusoutput(zip_cmd)
    commands.getstatusoutput(wget_cmd)
    os.rename(zip_pass_png_name, "解压密码，看这里.png")
    os.remove(file)

    os.chdir("..")
    commands.getstatusoutput(zip_cmd_no_pass)
    shutil.rmtree(dir_name)
    print("Success!")

def encrypt_dir(dirname):
    new_dir = "{} (双击解压)".format(dirname)
    shutil.copytree(src=dirname, dst=new_dir)
    os.chdir(new_dir)
    zip_cmd = '/usr/bin/zip -P "iswbm.com" "{}.zip" -r *'.format(dirname)
    zip_cmd_no_pass = '/usr/bin/zip -r "{}.zip" -r "{}"'.format(new_dir, new_dir)
    wget_cmd = '/usr/local/bin/wget -q http://image.iswbm.com/' + zip_pass_png_name

    commands.getstatusoutput(zip_cmd)
    commands.getstatusoutput(wget_cmd)
    os.rename(zip_pass_png_name, "解压密码，看这里.png")
    for home, dirs, files in os.walk("."):
        for file in files:
            if file in ("解压密码，看这里.png", "{}.zip".format(dirname)):
                continue
            os.remove(file)

        for dir in dirs:
            os.removedirs(dir)

    os.chdir("..")
    commands.getstatusoutput(zip_cmd_no_pass)
    shutil.rmtree(new_dir)
    print("Success!")

def encrypt(target):
    if os.path.isfile(target):
        encrypt_file(target)
    else:
        encrypt_dir(target)

for file in sys.stdin:
    dir,file = os.path.split(file.strip())
    os.chdir(dir)
    encrypt(file)