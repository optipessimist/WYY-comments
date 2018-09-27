# -*- coding: utf-8 -*-

    
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time,datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import pymysql
from pandas import DataFrame
from imageio import imread
import matplotlib.pyplot as plt
import jieba 
from wordcloud import WordCloud,ImageColorGenerator



class wyy():      #从网易云音乐获取评论并制作词云
    
    def __init__(self):
        self.url = 'https://music.163.com/'
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--disable-gpu')
        self.people = {'names':[], 'comments':[], 'dates':[], 'votes':[], 'replied_names':[], 'replied_comments':[]}
        self.isCN = 1     #默认启用中文分词
        self.back_coloring_path = r'D:\ciyun\background_image\mouse.jpg'  #设置背景图片路径#图片不同导致生成的image1能否有形状
        self.text_path = r'D:\ciyun\use.txt'   #设置要分析的文本路径
        self.font_path = r'D:\ciyun\youyuan.ttf' #设置中文字体路径
        self.stopwords_path = r'D:\ciyun\stopwords.txt'  #停用词词表
        self.imagename1 = r'D:\ciyun\defaultcolor.png'  #保存的图片名字1
        self.imagename2 = r'D:\ciyun\colorbyimage.png'   #保存的图片名字2
        self.my_word_list = []   #在jieba的词库中添加新词,这里未添加任何新词，根据时间自行添加
        

    def search(self,name):                 
        '根据歌名歌手来搜索歌曲'
        #self.driver = webdriver.Chrome()            #打开浏览器进行操作
        driver = webdriver.Chrome(chrome_options = self.chrome_options)   #无头模式的Chrome
        driver.get(self.url)
        time.sleep(0.5)
        driver.set_window_size(1280,800)               #在无头模式下把window_size放大以便能找到下面的‘srch’元素
        put = driver.find_element_by_id("srch")
        put.send_keys(name)
        time.sleep(0.5)
        put.send_keys(Keys.ENTER)
        time.sleep(2)
        wait = WebDriverWait(driver,10)
        wait.until(EC.presence_of_element_located((By.ID,'g_iframe')))
        driver.switch_to_frame('g_iframe')            #网页使用了iframe，需要进行读取
        time.sleep(1)
        put = driver.find_element_by_class_name('fst')        #选中单曲列表
        put.click()
        wait = WebDriverWait(driver,10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME,'w0')))
        music = driver.find_element_by_class_name('w0')
        music = music.find_element_by_class_name('text')
        music_lyrics = driver.find_element_by_class_name('w1').text
        music_name = driver.find_element_by_class_name('w0').text
        print('您搜索到的音乐是  '+music_name+'  '+music_lyrics)
        #因为歌名后可能有其他元素，使用下面的try语句
        try:
            music = music.find_element_by_class_name('s-fc7')
        except:
            pass
        music.click()
        time.sleep(1)
        return driver

    def lyrics_download(self,name):              #歌词下载
        try:
            driver = self.search(name)
            content = driver.page_source
            content = content.replace('<br />','\n')       #使输出结果更友好
            html = BeautifulSoup(content,'lxml')
            lyrics = html.find(id = 'lyric-content').text
            lyrics = '\n'.join(lyrics.split('\n')[:-1])     #把最后的‘展开’两个字取消
        finally:
            driver.close()
        return lyrics

    def download_next_page(self,driver):
        '获取下一页的html代码'
        time.sleep(0.5)
        next_page = driver.find_element_by_class_name('znxt')
        time.sleep(0.5)
        driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")  #把进度条来到翻页按钮处模仿用户操作
        next_page.click()
        wait = WebDriverWait(driver,10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME,'itm')))  #确保页面加载完成
        content = driver.page_source
        content = content.replace('<br />','\n')
        html = BeautifulSoup(content,'lxml')
        return html

    def download_previous_page(self,driver):
        '获取上一页的HTML代码'
        time.sleep(1)
        previous_page = driver.find_element_by_class_name('zprv')
        previous_page.click()
        wait = WebDriverWait(driver,10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME,'itm')))
        content = driver.page_source
        content = content.replace('<br />','\n')
        html = BeautifulSoup(content,'lxml')
        return html
    

    def change_time(self,time):
        '把时间格式统一为%Y-%m-%d %H:%M,但是时间过早的评论只显示了日期'
        now = datetime.datetime.now()
        day = now.strftime('%Y-%m-%d')
        year = now.strftime('%Y')
        '把时间转换为统一格式'
        if '昨天' in time:
            time = time.replace('昨天',day+' ')
        elif '前' in time:
            minut = int(time[:time.index('分')])
            time = (now + datetime.timedelta(minutes=-minut)).strftime('%Y-%m-%d %H:%M')
        elif len(time) == 5:
            time = day + ' ' + time
        elif time.index('月') == 1:
            time = time.replace('月','-').replace('日','')
            time = year+ '-' + time
        elif '年' in time:
            time = time.replace('年','-').replace('月','-').replace('日','')
        else:
            print('不明时间格式')
            return None
        return time


    def change_vote(self,vote):
        '确保评论的点赞数格式统一为int'
        try:
            change = vote[vote.index('(')+1:vote.index(')')]
            if '万' in change:
                change = int(float(change[:change.index('万')])*10000)
            else:
                change = int(change)
        except:
            change = 0
        return change    
        

    def one_page_comments_download(self,html):
        '收集用户评论的姓名，内容，时间，得赞数，针对谁的回复（姓名和内容）'
        persons = html.find_all(class_ = 'itm')
        for person in persons: 
            comment = person.find(class_ = 'cnt').text
            name = comment[:comment.index('：')]
            comment = comment[comment.index('：')+1:]
            date = person.find(class_ = 'time')
            date = self.change_time(date.text)
            vote = person.find(class_ = 'rp')
            try:
                vote = vote.text[vote.text.index('(')+1:vote.text.index(')')]
                vote = int(vote)
            except ValueError:
                vote = 0
            try:
                replied_comment = person.find(class_ = 'que').text
                if '删除' in replied_comment:                 #遇到’该评论已被删除‘
                    replied_comment = replied_comment
                    replied_name = None
                else:
                    replied_name = replied_comment[:replied_comment.index('：')]
                    replied_comment = replied_comment[replied_comment.index('：')+1:]
            except AttributeError as e:
                replied_comment = None
                replied_name = None
            self.people['names'].append(name)
            self.people['comments'].append(comment)
            self.people['dates'].append(date)
            self.people['votes'].append(vote)
            self.people['replied_names'].append(replied_name)
            self.people['replied_comments'].append(replied_comment)
            
        
    def great_comments(self,name = '等你下课 周杰伦'):          #只获取点赞数最多的不超过15条评论
        '获得在第一个页面上的精彩评论（至多15条）'
        try:
            browser = self.search(name)
            wait = WebDriverWait(browser,10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME,'itm')))
            content = browser.page_source
            content = content.replace('<br />','\n')
            html = BeautifulSoup(content,'lxml')
            great = {'names':[], 'comments':[], 'dates':[], 'votes':[], 'replied_names':[], 'replied_comments':[]}
            persons = html.find_all(class_ = 'itm')
            for person in persons[0:15]: 
                comment = person.find(class_ = 'cnt').text
                name = comment[:comment.index('：')]
                comment = comment[comment.index('：')+1:]
                date = person.find(class_ = 'time')
                date = self.change_time(date.text)
                vote = person.find(class_ = 'rp')
                vote = self.change_vote(vote.text)
                if vote < 10:      #可能一首歌并没有15条点赞数最多的评论
                    break
                try:
                    replied_comment = person.find(class_ = 'que').text
                    replied_name = replied_comment[:replied_comment.index('：')]
                    replied_comment = replied_comment[replied_comment.index('：')+1:]
                except AttributeError as e:
                    replied_comment = None
                    replied_name = None
                    #print(e)
                great['names'].append(name)
                great['comments'].append(comment)
                great['dates'].append(date)
                great['votes'].append(vote)
                great['replied_names'].append(replied_name)
                great['replied_comments'].append(replied_comment)
            print('获取了点赞数最多的评论')
        finally:
            browser.close()
        return great


    def save_mysql(self,people):
        '把获取的数据存入数据库'
        db = pymysql.connect(host = 'localhost', port = 3306 ,user = 'root', passwd = 'your password', db = 'your db', charset='utf8mb4')     #使用utf8mb4来显示一些表情符号等等
        cursor = db.cursor()
        sql1 = 'USE text'
        sql2 = 'INSERT INTO wyycomments (name, own_comment, vote, date, replied_name, replied_comment) VALUES (%s,%s,%s,%s,%s,%s)'
        for i in range(len(people['names'])):
            try:
                cursor.execute(sql1)
                cursor.execute(sql2,(people['names'][i],people['comments'][i],people['votes'][i],people['dates'][i],people['replied_names'][i],people['replied_comments'][i]))
                cursor.connection.commit()
            except Exception as e:
                print(e)
                db.rollback()
                continue
        cursor.close()
        db.close()
        
        
    def save_csv(self,people):
        '把获取的数据存入csv文件中'
        people = DataFrame(people)
        people.to_csv('D:\\wyy_comments.csv',encoding = 'utf_8_sig')
        #因为根据评论制作词云，所以单独再输出下面的txt文件
        people.to_csv('D:\\ciyun\\use.txt',columns = ['comments'],index = 0,header = 0)
        
    
    def collect_comments(self,n=1,name = '云烟成雨',style = []):          #默认是我特别喜欢的一首民谣
        'n是想要爬取的页码，name是要爬取的歌名，style可以选择mysql和csv的存储方式,获取评论'
        driver = self.search(name)
        html = []
        if n<1:
            print('抱歉，您至少得爬一页吧')
            driver.close()
            return None
        elif n>=1:
            try:
                self.download_next_page(driver)
                html.append(self.download_previous_page(driver))
                self.one_page_comments_download(html[0])
                print('获取了第1页的评论')
                for i in range(int(n-1)):
                    html.append(self.download_next_page(driver))
                    self.one_page_comments_download(html[i])
                    print('获取了第'+str(i+2)+'页的评论')
                    time.sleep(0.5)
                    #print('获取了第'+k+'页的评论')
                if 'mysql' in style:
                    self.save_mysql(self.people)
                    print('存储入MySQL')
                if 'csv' in style:
                    self.save_csv(self.people)
                    print('存储入csv')
            except Exception as e:
                print(e)
            finally:
                driver.close()
                return self.people


    def make_ciyun(self):
        '根据评论生成词云'
        back_coloring = imread(self.back_coloring_path)  #设置背景图片

        #设置词云属性
        wc = WordCloud(background_color="white",#背景颜色
                       max_words = 500,#词云显示的最大词数
                       mask = back_coloring, #设置背景图片
                       max_font_size = 150, #字体最大值
                       font_path = self.font_path,#设置字体
                       random_state = 42,
                       width = 1000,height = 860,margin = 2,#设置图片默认的大小,但是如果使用背景图片的话,那么保存的图片大小将会按照其大小保存,margin为词语边缘距离
                       )

        #添加自己的词库分词
        def add_word(list):
            for items in list:
                jieba.add_word(items)
                
        add_word(self.my_word_list)
                
        tete = open(self.text_path,encoding='utf-8').read()
    
        def jiebaclearText(text):
            mywordlist = []
            seg_list = jieba.cut(text,cut_all=False)
            liststr = '/'.join(seg_list)
            f_stop = open(self.stopwords_path)
            try:
                f_stop_text = f_stop.read()
            finally:
                f_stop.close()
                f_stop_seg_list = f_stop_text.split('\n')
            for myword in liststr.split('/'):
                if not(myword.strip() in f_stop_seg_list) and len(myword.strip())>1:
                    mywordlist.append(myword)
            return '\n'.join(mywordlist)
    
        if self.isCN:
            text = jiebaclearText(tete)

        # 生成词云, 可以用generate输入全部文本(wordcloud对中文分词支持不好,建议启用中文分词),也可以我们计算好词频后使用generate_from_frequencies函数

        wc.generate(text)

        # wc.generate_from_frequencies(txt_freq)
        # txt_freq例子为[('词a', 100),('词b', 90),('词c', 80)]
        # 从背景图片生成颜色值
        #image_colors = ImageColorGenerator(back_coloring)
    
    
        plt.figure()
        #以下代码显示图片
        plt.imshow(wc)
        plt.axis('off')
        plt.show()
        #绘制词云
        
        # 保存图片
        wc.to_file(self.imagename1)
        

        image_colors = ImageColorGenerator(back_coloring)


        plt.imshow(wc.recolor(color_func=image_colors))
        plt.axis("off")
        # 绘制背景图片为颜色的图片
        plt.figure()
        plt.imshow(back_coloring, cmap=plt.cm.gray)
        plt.axis("off")
        plt.show()
        #保存图片
        wc.to_file(self.imagename2)



text = wyy()

#获取评论并存入数据库和csv、txt文档
end = text.collect_comments(1000,'追梦赤子心',['csv'])
#制作词云
text.make_ciyun()

#获取点赞最多的评论
#great = text.great_comments('记得')

#获取歌词
#lyric = text.lyrics_download('偏爱')


    
    
    


