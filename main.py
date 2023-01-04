import requests
from bs4 import BeautifulSoup as bs
import telebot
import schedule
import time

from app import TOKEN

bot = telebot.TeleBot(TOKEN)


class Info:
    def __init__(self):
        self.chat = 0
        self.chatid = {}
        self.status = {}

    def reminder(self, userid, resp):
        self.chatid[userid] = resp


info = Info()

file = open('dict.txt', 'r')
dic = {}

while True:
    line = file.readline()

    if not line:
        break
    else:
        line = line.replace('\n', '').split('-')
        dic[line[0]] = line[1]

file.close()


# декоратор команды start
@bot.message_handler(commands=['start'])
def start(msg):
    info.chat = msg.chat.id
    if msg.chat.id in info.chatid.keys():
        pass
    else:
        info.chatid[msg.chat.id] = False
        info.status[msg.chat.id] = False

    bot.send_message(chat_id=msg.chat.id,
                     text='💤 Вас приветствует помощник чтения снов!\n\n'
                          '*Сон* - это состояние человеческого организма, '
                          'когда все тело отдыхает после дневных нагрузок. Но наш мозг, наше сознание и '
                          'подсознание никогда не прекращают работать, анализировать и мечтать. '
                          'И эта деятельность проявляется в наших сновидениях.',
                     parse_mode='Markdown')
    bot.send_message(chat_id=msg.chat.id,
                     text='Напишите *одним словом* тематику сна 👇\n'
                          '*Например:* сад',
                     parse_mode='Markdown')


# функция напоминая о сне по утрам
def job():
    bot.send_message(chat_id=info.chat, text='Доброе утро! Расскажи, что снилось? 🙂',
                     parse_mode='Markdown')


# декоратор обработки ответа на уведомления
@bot.message_handler(func=lambda message: message.text in ['Да', 'Нет', 'да', 'нет'])
def reminder(msg):
    if msg.text.lower() == 'да':
        # включаем уведомления на 9:30 утра
        resp = True
        info.reminder(msg.chat.id, resp)
        schedule.every().day.at("09:30").do(job)

        bot.send_message(chat_id=msg.chat.id, text='Уведомления успешно включены!\n',
                         parse_mode='Markdown')
        bot.send_message(chat_id=msg.chat.id, text='Введите новое *слово* ниже 👇',
                         parse_mode='Markdown')
    else:
        resp = False
        info.reminder(msg.chat.id, resp)
        bot.send_message(chat_id=msg.chat.id, text='Очень жаль 😢\n'
                                                   'Если захотите включить уведомления, просто напишите "*Да*"',
                         parse_mode='Markdown')
        bot.send_message(chat_id=msg.chat.id, text='Введите новое *слово* ниже 👇',
                         parse_mode='Markdown')

    while info.chatid[info.chat]:
        schedule.run_pending()
        time.sleep(1)


# декоратор для обработки любого текста
@bot.message_handler(content_types=["text"])
def get_text(msg):
    first_letter = msg.text[0].lower()

    get_info(dic[first_letter], msg.text.lower(), msg)  # функция работы со ссылкой


def get_info(letter, text, msg):
    ans = []  # конечный массив, собирающий заголовки и текст под ними
    txt = ''  # финальный ответ, который поступит пользователю

    request = requests.get(url=f'http://sonnik.favorites.com.ua/vse-sonniki/{letter}/')  # заход на сайт
    soup = bs(request.content, 'html.parser')

    words = {}  # словарь для сбора доступных слов

    # сбор всех доступных слов, начинающихся с указанной буквы
    for elem in soup.find('div', {'id': 'words'}):
        try:
            words[elem.text] = elem.get('href')
        except Exception:
            continue

    try:
        # пробуем зайти на сайт с указанным словом: если слова не найдется в словаре, то об этом будет сообщено
        son = requests.get(url=f'http://sonnik.favorites.com.ua/vse-sonniki/{letter}/{words[text]}')
        another_soup = bs(son.content, 'html.parser')

        name = []  # список заголовков
        texts = []  # список текстов под заголовками

        # сбор основного текста с сайта
        txt += '*' + str(another_soup.find('h3').text.capitalize()) + '*' + '\n'
        txt += str(another_soup.find('p').text) + '\n\n'

        for i in another_soup.find_all('h2'):
            name.append(i.text)
        for j in another_soup.find_all('p')[1:-1]:
            q = j.text.replace('\xa0', '').split('. ')
            a = '. '.join(q)
            texts.append(a[0].upper() + a[1:])

        try:
            # если на сайте есть "альтернативное толкование", обработаем это
            if texts[0].lower() == 'альернативное толкование:' or texts[0].lower() == 'альтернативное толкование:':
                txt += '*Альтернативное толкование:*\n'
                del texts[0]

                txt += str(texts[0]) + '\n\n'
                del texts[0]
        except Exception:
            pass

        # формирование единого массива с заголовками и текстами
        for n, t in zip(name, texts):
            ans.append(f"*{n}*\n{t}\n")

        # проверка на длину сообщения: если оно меньше 4096 знаков => добавим в финальный текст значение из `ans`
        n = 0
        while len(txt) + len(str(ans[n]) + '\n') < 4096:
            txt += str(ans[n]) + '\n'
            if n == len(ans) - 1:
                break
            else:
                n += 1

        # отправка конечного сообщения с текстом
        bot.send_message(chat_id=msg.chat.id, text=txt, parse_mode='Markdown')

        # если сообщений было первое, спросим у пользователя об уведомлениях (нужно или нет)
        if not info.status[msg.chat.id]:
            info.status[msg.chat.id] = True
            bot.send_message(chat_id=msg.chat.id, text='Хотите включить напоминая по утрам?\n'
                                                       'В ответ напишите: *Да* или *Нет*',
                             parse_mode='Markdown')
        else:  # если сообщение не первое, то спрашивать не будем
            bot.send_message(chat_id=msg.chat.id, text='Введите новое *слово* ниже 👇', parse_mode='Markdown')

    except Exception as e:
        print(e)
        bot.send_message(chat_id=msg.chat.id, text='Слова не нашлось, попробуйте другое')


bot.polling(none_stop=True)
