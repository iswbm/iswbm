#!/Users/MING/.virtualenvs/werobot/bin/python

'''
Author: wangbm
Email: wongbingming@163.com
Wechat: stromwbm
Blog: iswbm.com
公众号：Python编程时光


Created: 2021/2/28 下午4:10
Updated: 2021/5/23 上午11:00
'''

import io
import os
import math
import time

from PIL import Image, ImageGrab, ImageFont, ImageDraw, ImageChops, ImageEnhance
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


SIZE = 50
QUALITY = 80
ANGLE = 30
SPACE = 150
OPACITY = 0.2
COLOR = "#8B8B1B"
MARK = "微信公众号: Python编程时光"
TTF_FONT = "/System/Library/Fonts/STHeiti Medium.ttc"


def crop_image(im):
    '''裁剪图片边缘空白'''
    bg = Image.new(mode='RGBA', size=im.size)
    diff = ImageChops.difference(im, bg)
    del bg
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im

def set_opacity(im, opacity):
    '''
    设置水印透明度
    '''
    assert opacity >= 0 and opacity <= 1

    alpha = im.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    im.putalpha(alpha)
    return im


def gen_mark():
    '''
    生成mark图片，返回添加水印的函数
    '''
    # 字体宽度
    width = len(MARK) * SIZE

    # 创建水印图片(宽度、高度)
    mark = Image.new(mode='RGBA', size=(width, SIZE))

    # 生成文字
    draw_table = ImageDraw.Draw(im=mark)
    draw_table.text(xy=(0, 0),
                    text=MARK,
                    fill=COLOR,
                    font=ImageFont.truetype(TTF_FONT,
                                            size=SIZE))
    del draw_table

    # 裁剪空白
    mark = crop_image(mark)

    # 透明度
    set_opacity(mark, OPACITY)

    def mark_im(im):
        ''' 在im图片上添加水印 im为打开的原图'''

        # 计算斜边长度
        c = int(math.sqrt(im.size[0]*im.size[0] + im.size[1]*im.size[1]))

        # 以斜边长度为宽高创建大图（旋转后大图才足以覆盖原图）
        mark2 = Image.new(mode='RGBA', size=(c, c))

        # 在大图上生成水印文字，此处mark为上面生成的水印图片
        y, idx = 0, 0
        while y < c:
            # 制造x坐标错位
            x = -int((mark.size[0] + SPACE)*0.5*idx)
            idx = (idx + 1) % 2

            while x < c:
                # 在该位置粘贴mark水印图片
                mark2.paste(mark, (x, y))
                x = x + mark.size[0] + SPACE
            y = y + mark.size[1] + SPACE

        # 将大图旋转一定角度
        mark2 = mark2.rotate(ANGLE)

        # 在原图上添加大图水印
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
        im.paste(mark2,  # 大图
                 (int((im.size[0]-c)/2), int((im.size[1]-c)/2)),  # 坐标
                 mask=mark2.split()[3])
        del mark2
        return im

    return mark_im


def notify_to_mac(message):
    os.system("osascript -e 'display notification \"{}\"\'".format(message))

def make_watermark(image):
    marker = gen_mark()
    out = marker(image)
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


