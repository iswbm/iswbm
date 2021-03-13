#!/Users/MING/.virtualenvs/werobot/bin/python

'''
Author: wangbm
Email: wongbingming@163.com
Wechat: stromwbm
Blog: iswbm.com
公众号：Python编程时光


date: 2021/2/28 下午4:10
desc:
'''

import io
import time
import os
from PIL import Image, ImageGrab, ImageFont, ImageDraw
from pynput import keyboard
from pykeyboard import PyKeyboard
import pasteboard


key_list = []
upload_pic_set = {
    keyboard.Key.ctrl.value.vk,
    keyboard.Key.cmd.value.vk,
    keyboard.Key.alt.value.vk,
    keyboard.KeyCode(35).vk
}


def notify_to_mac(message):
    os.system("osascript -e 'display notification \"{}\"\'".format(message))

def make_watermark(image):
    txt = Image.new('RGBA', image.size, (0, 0, 0, 0))
    fnt = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 20)
    draw = ImageDraw.Draw(txt)
    draw.text(((txt.size[0]-300)//2, txt.size[1]-40), "微信公众号: Python编程时光", font=fnt, fill=(240, 49, 48, 255))
    out = Image.alpha_composite(image, txt)
    return out

def put_image_to_clip(image):
    img_byte_arr = io.BytesIO()  # BytesIO实现了在内存中读写bytes
    pb = pasteboard.Pasteboard()

    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    pb.set_contents(img_byte_arr, pasteboard.PNG)
    # https://developer.apple.com/documentation/appkit/nspasteboardtypestring?language=objc

def get_image_from_clipboard():
    img_rgb = ImageGrab.grabclipboard()
    image = img_rgb.convert("RGBA")
    return image

def upload_image_via_picgo():
    k = PyKeyboard()
    k.press_keys(['Command', 'shift', 'p'])

def on_press(key):
    if isinstance(key, keyboard.KeyCode):
        key_list.append(key.vk)
    elif isinstance(key, keyboard.Key):
        key_list.append(key.value.vk)

    if set(key_list) == upload_pic_set:
        image = get_image_from_clipboard()
        new_image = make_watermark(image)
        put_image_to_clip(new_image)
        upload_image_via_picgo()
        time.sleep(2)
        notify_to_mac("成功添加水印并上传到图床")


def on_release(key):
    key_list.clear()

with keyboard.Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()


