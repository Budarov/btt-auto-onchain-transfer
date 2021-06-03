import requests
import json
from datetime import datetime
import os.path, sys
import time
import locale

# Указываем ваш порт speed.btt.network
speed_btt_port = 54426

# Минимальный баланс на шлюзе, с учетом знаков после запятой.
# Т.е. 1000 Btt = 1000.000000 Btt. В переменную пишем без точки. 
min_tronscan_balance = 5000000000

# Сколько переводим за раз.
# Должно быть больше 1000 Btt, т.е. минимум 1000000000
min_transfer_sum = 1000000000

# Время задержки между попытками в секундах
time_to_try = 5

# Время задержки между попытками в секундах при наличии 
# Btt на шлюзе больше, чем min_tronscan_balance
turbo_time_to_try = 1

# Количество строк в log файле
log_len = 1000

old_tronscan_balance = 0

#Узнаём locale системы
sys_lang = locale.getdefaultlocale()[0]

# Пишем сообщения в log файл и выводим их в консоль
def to_log(massage, to_file):
    #Получаем текующие дату и время
    massage = ' ' + massage
    current_time = datetime.now()
    current_time = current_time.strftime("%d-%m-%Y, %H:%M:%S")
    if to_file:
        if os.path.isfile(sys.path[0] + '\\btt-auto-transfer.log'):
            log_file = open(sys.path[0] + '\\btt-auto-transfer.log', 'r')
            log_file_lines = log_file.readlines()
            if len(log_file_lines) >= log_len:
                cut_len = len(log_file_lines) - log_len
                for ln in range(cut_len + 1):
                    log_file_lines.pop(0)
                log_file = open(sys.path[0] + '\\btt-auto-transfer.log', 'w')
                for ln in range(len(log_file_lines)):
                    log_file.write(str(log_file_lines[ln]))
            else:
                log_file = open(sys.path[0] + '\\btt-auto-transfer.log', 'a')
        else:
            log_file = open(sys.path[0] + '\\btt-auto-transfer.log', 'w')
    print(current_time + massage)
    if to_file:
        log_file.write(current_time + massage + '\n')
        log_file.close()


# Получаем токен BTT Speed
def get_token(port):
    try:
        token_res = requests.get('http://127.0.0.1:' + str(port) + '/api/token')
        token = token_res.text
    except requests.ConnectionError:
        if sys_lang == 'ru_RU':
            to_log('Не удалось получить токен BTT Speed по адресу: ' + 'http://127.0.0.1:' + str(port) + '/api/token' + ' Указан неверный порт или не запущен BTT Speed.', True)
        else:
            to_log('Failed to get BTT Speed token at address: ' + 'http://127.0.0.1:' + str(port) + '/api/token' + ' Wrong port in settings or BTT speed not running.', True)
        return ''
    return token

# Получаем баланс In App
def get_balance(port, token):
    if token == '':
        return 0
    balance_res = requests.get('http://127.0.0.1:' + str(port) + '/api/status?t=' + token)
    balance = json.loads(balance_res.text)
    return balance['balance']

# Получаем баланс на шлюзе
def get_tronscan_balance():
    try:
        balance_res = requests.get('https://apiasia.tronscan.io:5566/api/account?address=TA1EHWb1PymZ1qpBNfNj9uTaxd18ubrC7a')
        balance = json.loads(balance_res.text)
        sa = list(filter(lambda tokenBalances: tokenBalances['tokenId'] == '1002000', balance["tokenBalances"]))
    except requests.ConnectionError:
        if sys_lang == 'ru_RU':
            to_log('Не удалось узнать баланc шлюза по адресу https://apiasia.tronscan.io:5566/api/account?address=TA1EHWb1PymZ1qpBNfNj9uTaxd18ubrC7a сайт недоступен.', True)
        else:
            to_log('Failed get balance of gateway at address https://apiasia.tronscan.io:5566/api/account?address=TA1EHWb1PymZ1qpBNfNj9uTaxd18ubrC7a site unavailable.', True)
        return 0
    try:
        res = int(sa[0]['balance'])
    except IndexError:
        if sys_lang == 'ru_RU':
            to_log('Пришел не валидный json от https://apiasia.tronscan.io:5566/api/account?address=TA1EHWb1PymZ1qpBNfNj9uTaxd18ubrC7a', True)
        else:
            to_log('Not valid json from https://apiasia.tronscan.io:5566/api/account?address=TA1EHWb1PymZ1qpBNfNj9uTaxd18ubrC7a', True)
        return 0
    return res
    
# Переводим из In App в On Chain
# Возвращает id перевода    
def tranfer(port, token, transfer_sum):
    transfer_post = requests.post('http://127.0.0.1:' + str(port) + '/api/exchange/withdrawal?t=' + token + '&amount=' + str(transfer_sum))
    return transfer_post.text

# Проверка параметра одноразового запуска -onerun
onerun = False
if len(sys.argv) > 2:
    if sys_lang == 'ru_RU':
        sys.exit("Скрипт имеет только один аргумент: -onerun, выход.")
    else:
	    sys.exit("Script has only one argument: -onerun, exit.")
elif len(sys.argv) == 2:
    if sys.argv[1] == "-onerun":
        if sys_lang == 'ru_RU':
            to_log("------ Скрипт выполнится один раз. ------", False)
        else:
            to_log("------ One-run mode on. ------", False)
        onerun = True
    else:
        if sys_lang == 'ru_RU':
            sys.exit("Скрипт имеет только один аргумент: -onerun, выход.")
        else:
	        sys.exit("Script has only one argument: -onerun, exit.")

def try_tranfer(onerun, sleep_time):
    global old_tronscan_balance
    token = get_token(speed_btt_port)
    balance = get_balance(speed_btt_port, token)
    tronscan_balance = get_tronscan_balance()

    if (token != "") and (tronscan_balance > 0):
        if (tronscan_balance >= min_tronscan_balance) and (balance >= min_transfer_sum):
            if sys_lang == 'ru_RU':
                to_log('Выполняется перевод. Баланс шлюза: ' + str(tronscan_balance / 1000000) + ' Btt. Баланс In App: ' + str(balance / 1000000) + ' Btt.', True)
            else:
                to_log('Transfer in progress. Gateway balance: ' + str(tronscan_balance / 1000000) + ' Btt. Balance In App: ' + str(balance / 1000000) + ' Btt.', True)
            tr = tranfer(speed_btt_port, token, min_transfer_sum)
            if sys_lang == 'ru_RU':
                to_log('id транзакции: ' + tr, True)
            else:
                to_log('transaction id: ' + tr, True)
            sleep_time = turbo_time_to_try
        else:
            if (old_tronscan_balance // 1000000) == (tronscan_balance // 1000000):
                if sys_lang == 'ru_RU':
                    to_log('Недостаточно средств In App или на шлюзе. Баланс шлюза: ' + str(tronscan_balance / 1000000) + ' Btt. Баланс In App: ' + str(balance / 1000000) + ' Btt.', False)
                else:
                    to_log('Not enough In App or Gateway funds. Gateway balance: ' + str(tronscan_balance / 1000000) + ' Btt. Balance In App: ' + str(balance / 1000000) + ' Btt.', False)
            else:
                if sys_lang == 'ru_RU':
                    to_log('Недостаточно средств In App или на шлюзе. Баланс шлюза: ' + str(tronscan_balance / 1000000) + ' Btt. Баланс In App: ' + str(balance / 1000000) + ' Btt.', True)
                else:
                    to_log('Not enough In App or Gateway funds. Gateway balance: ' + str(tronscan_balance / 1000000) + ' Btt. Balance In App: ' + str(balance / 1000000) + ' Btt.', True)
            old_tronscan_balance = tronscan_balance
            sleep_time = time_to_try
    else:
        to_log('Не все необходимые данные удалось получить.', False)
    if not onerun:
        time.sleep(sleep_time)
        try_tranfer(onerun, sleep_time)


try_tranfer(onerun, time_to_try)
    