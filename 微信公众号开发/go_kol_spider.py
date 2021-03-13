import requests
import xlwings as xw
from bs4 import BeautifulSoup


app = xw.App(visible=True, add_book=False) # 程序可见，只打开不新建工作薄
app.display_alerts = False # 警告关闭
app.screen_updating = False # 屏幕更新关闭
# wb = app.books.open(xls_path)
wb = app.books.open("./articles_from_20cimi.xlsx")

sht = wb.sheets[0]

nickname_file = open("nickname_file.txt", "w")

i = 1

def is_url(url):
    return "http" in url

def get_nickname_from_url(url):
    global i
    response = requests.get(url)

    soup = BeautifulSoup(response.text, "html.parser")
    results = soup.find_all(name="strong", attrs={"class": "original_primary_nickname"})
    for result in results:
        info = f"第 {i} 个公众号获取完成：{result.string}"
        nickname_file.write(info+"\n")
        print(info)
        i += 1


for url in sht.range('g1:g2243').value:
    if is_url(url):
        get_nickname_from_url(url)

wb.close() # 关闭文件
app.quit() # 关闭程序