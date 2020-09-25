from telegram.ext import Updater, CommandHandler, MessageHandler
from bs4 import BeautifulSoup
from secret import TOKEN
import random
import requests
import pandas
import re
from collections import defaultdict


url_market = 'https://www.gazzetta.it/Calciomercato/serie-A/'
url_squads = 'https://sport.virgilio.it/calcio/squadre/'
url_quotes = 'https://www.fantacalcio.it/quotazioni-fantacalcio/mantra'
prefix = 'https://www.fantacalcio.it/squadre/'
xlsx = 'Listone_Fantacalcio_Mantra.xlsx'
pandas.options.display.max_colwidth = 100
roles = {"P":"Portiere", "Por": "Portiere", "D": "Difensore", "Dd": "Difensore", "Ds": "Difensore",
         "Dc": "Difensore", "E": "Centrocampista", "M": "Centrocampista", "C": "Centrocampista",
         "W": "Trequartista", "T": "Trequartista", "A": "Attaccante", "Pc": "Attaccante"}
chosen_dict = defaultdict(lambda: defaultdict(set))
player_url_dict = {}
is_mantra = True

def classic(bot, update):
    global is_mantra
    is_mantra = False
    roles["W"] = "Centrocampista"
    roles["T"] = "Centrocampista"
    global xlsx
    xlsx = 'Listone_Fantacalcio_Classic.xlsx'
    refresh(bot, update)
    chat_id = update.message.chat_id
    bot.send_message(chat_id=chat_id, text="Modalità Classic")

def mantra(bot, update):
    global is_mantra
    is_mantra = True
    roles["W"] = "Trequartista"
    roles["T"] = "Trequartista"
    global xlsx
    xlsx = 'Listone_Fantacalcio_Mantra.xlsx'
    refresh(bot, update)
    chat_id = update.message.chat_id
    bot.send_message(chat_id=chat_id, text="Modalità Mantra")

def get_squads(url):
    """Used to get all 20 Serie A squads from a specific URL"""
    source = requests.get(url).text
    soup = BeautifulSoup(source, 'lxml')
    body = soup.find('body')
    article = body.find('div', class_='m-container')\
        .find('section', class_='m-grd m-content')\
        .find('div', class_='colSx')\
        .find('section', class_='elenchi')\
        .find('ul', class_='elenco-grd').text

    return article.strip().split(' ')


def get_file(url, image):
    """Used to get a file from an URL"""
    contents = requests.get(url).json()
    file = contents[image]
    return file


def start(bot, update):
    """Define the /start command behaviour"""
    with open("start.txt", 'r') as file:
        data = file.read()
    chat_id = update.message.chat_id
    bot.send_message(chat_id=chat_id, text=data)


def help(bot, update):
    """Define the /help command behaviour"""
    with open("help.txt", 'r') as file:
        data = file.read()

    chat_id = update.message.chat_id
    bot.send_message(chat_id=chat_id, text=data)


def cat(bot, update):
    """Define the /cat command behaviour"""
    file = get_file('http://aws.random.cat/meow', 'file')
    chat_id = update.message.chat_id
    bot.send_photo(chat_id=chat_id, photo=file)


def dog(bot, update):
    """Define the /dog command behaviour"""
    url = get_file('https://random.dog/woof.json', 'url')
    chat_id = update.message.chat_id
    bot.send_photo(chat_id=chat_id, photo=url)


def squad_market_info():
    """Used to get all transfer market information about a team"""
    source = requests.get(url_market).text
    soup = BeautifulSoup(source, 'lxml')
    body = soup.find('body')
    article = body.find('main', id='l-main')\
        .find('div', class_='wrapper has-border')\
        .find('div', class_='container')\
        .find('section', class_='body-hp')\
        .find('div', class_='columns')\
        .find('div', class_='column is-8 section-page-list')\
        .find_all('div', class_='bck-list-market')

    squads = []
    for squad in article:
        squads.append(squad.text)

    format_squad = []
    for transfer in squads:
        transfer = re.sub('(Allenatore)', r'\n\n\1', transfer)
        transfer = re.sub('(Acquisti)', r'\n\n\1\n ', transfer)
        transfer = re.sub('(Cessioni)', r'\n\n\1\n ', transfer)
        transfer = re.sub('(Obiettivi)', r'\n\n\1\n ', transfer)
        transfer = re.sub(r'(\),)', r'\1\n', transfer)
        transfer = transfer.replace("Acquisti", "ACQUISTI")
        transfer = transfer.replace("Cessioni", "CESSIONI")
        transfer = transfer.replace("Obiettivi", "OBIETTIVI")
        transfer = transfer.replace("Il MercatoCosì in campo", " ")
        format_squad.append(transfer)

    return format_squad


def get_squad_function(squad_index):
    """Used to get all teams' commands about transfer market"""
    def result(bot, update):
        """Used to send to bot all transfer market information about a team"""
        chat_id = update.message.chat_id
        bot.send_message(
            chat_id=chat_id, text=squad_market_info()[squad_index])
    return result


def get_role_function(selected_role):

    def role_func(bot, update):
        chatID = update.message.chat.id
        role = get_multiple_roles()
        players = {row['Id']: row for _, row in role.iterrows(
        ) if row['Main Role'] == selected_role}
        chosen_ids = chosen_dict[chatID][selected_role]
        available_ids = set(players) - chosen_ids

        if len(available_ids) == 0:
            chosen_ids.clear()
        else:
            playerID = random.sample(available_ids, 1)[0]
            chosen_ids.add(playerID)
            player = players[playerID]
            name = player['Nome']
            squad = player['Squadra']
            r = player['R']
            qta = player['Qt. A']
            final = (
                f'Nome:\t\t\t\t\t\t\t{name}\nSquadra:\t\t\t{squad}\nRuoli:\t\t\t\t\t\t\t\t\t{r}\nQt. A:\t\t\t\t\t\t\t\t\t{qta}')
            bot.send_message(chat_id=chatID, text=final)

            if len(available_ids) == 1:
                bot.send_message(
                    chat_id=chatID, text="Giocatori terminati! Scegli un ruolo per riprendere l'asta")

    return role_func


def get_players_name():

    xls = pandas.read_excel(xlsx, skiprows=1)
    player_names = []
    nome = ""
    for name in xls['Nome']:
        nome = name.replace('\'', '')\
               .replace('.', '')\
               .replace('-', '')
        player_names.append(str(nome.replace(' ', '')))

    return(player_names)


def get_players_url():

    global player_url_dict
    xls = pandas.read_excel(xlsx, skiprows=1)
    for _, data in xls.iterrows():
        ID = data['Id']
        name = data['Nome'].replace('\'', '')\
               .replace('-', '')\
               .replace('.', '')\
               .replace(' ', '')
        squad = data['Squadra']
        player_url = prefix + squad + '/' + name + '/' + str(ID)
        player_url_dict.update({name: player_url})


def get_player_info_function(selected_player):

    def player_info_func(bot, update):

        source = requests.get(player_url_dict[selected_player])
        soup = BeautifulSoup(source.text, 'lxml')
        body = soup.find('body')
        article = body.find('div', class_='container article-page')\
            .find('div', class_='row full-width')\
            .find('main', class_='col-xs-12 col-md-8 px-0')\
            .find('div', class_='col-left rel')\
            .find('div', id='singleCont')\
            .find('div', id='artsingle')\
            .find('div', class_='row pb article-lpad no-gutter')\
            .find('div', id='artContainer')\
            .find('div', class_='stickem-container')\
            .find('div', id='fantastatistiche')\
            .find('div', class_='col-lg-12 col-md-12 col-sm-12 col-xs-12 lbox2 sqcard gutter5').text
        
        article = re.sub('2020-21FantacalcioStatisticoItalia', '\n\n', article)
        article = re.sub('\(Fantacalcio.it\)', '', article)
        article = re.sub('Fantastatistiche ', 'FANTASTATISTICHE\n\n', article)
        article = re.sub('(PARTITE GIOCATE\\s)', r' - \1\n', article)
        article = re.sub('(GOL FATTI\\s)', r' - \1\n', article)
        article = re.sub('(GOL SUBITI\\s)', r' - \1\n', article)
        article = re.sub('(AMMONIZIONI\\s)', r' - \1\n', article)
        article = re.sub('(ESPULSIONI\\s)', r' - \1\n', article)
        article = re.sub('ASSISTASSIST', ' - ASSIST | ASSIST', article)
        article = re.sub('(RIGORI)', r' - \1 ', article)
        article = re.sub('(PARATI\\s)', r'\1\n', article)
        article = re.sub('(SEGNATI/CALCIATI)', r'\1\n', article)
        article = re.sub('VOTO E FANTAVOTO  ', '', article)
        article = re.sub('QUOTAZIONE', '', article)
        article = re.sub(' \\d+,\\d+INIZIALE\\d+,\\d+ATTUALEPRESENZE', '', article)
        article = re.sub('(FERMO)', r'\1\n', article)
        article = re.sub('(su)', r' \1 ', article)
        article = re.sub('(MEDIA VOTO)', r' - \1\n', article)
        article = re.sub('(MEDIA FANTAVOTO\\s)', r' - \1\n', article)
        article = re.sub('(STATUS\\s)', r' - \1\n', article)
        article = re.sub('\\d+ª giornataBONUS/MALUS \\d+,\\dSOMMA BONUS MALUS \\d+ª giornata', ' ', article)

        chat_id = update.message.chat_id
        bot.send_message(chat_id=chat_id, text=article)

    return player_info_func


def progress(bot, update):
    """Define the /progress command behaviour"""
    chatID = update.message.chat_id
    role = get_multiple_roles()
    user_dict = chosen_dict[chatID]
    final = ""
    tot_players, tot_chosen = 0, 0
    if (is_mantra): list_p = ["Portiere", "Difensore", "Centrocampista", "Trequartista", "Attaccante"]
    else: list_p = ["Portiere", "Difensore", "Centrocampista", "Attaccante"]
    for key in list_p:
        n_players = len([row['Id']
                         for _, row in role.iterrows() if row['Main Role'] == key])
        n_chosen = len(user_dict[key])
        tot_players += n_players
        tot_chosen += n_chosen
        final += f'{key}:\t\t{n_chosen}\\{n_players}\n'
    final += f'\n\nTOTALI:\t\t{tot_chosen}\\{tot_players}'
    bot.send_message(chat_id=chatID, text=final)


def get_multiple_roles():
    """used to assign each player a main role"""     
    xls = pandas.read_excel(xlsx, skiprows=1) 
    xls['R1'] = list(map(lambda x: x.split(';')[0], xls['R']))
    xls['Main Role'] = list(map(lambda x: roles[x], xls['R1']))
    return xls


def nomesquadra(bot, update):
    """Define the /nomesquadra command behaviour"""
    with open("nomesquadra.txt", 'r') as file:
        data = file.read()

    chat_id = update.message.chat_id
    bot.send_message(chat_id=chat_id, text=data)


def ruolo(bot, update):
    """Define the /ruolo command behaviour"""
    if (is_mantra):
        with open("ruolo_mantra.txt", 'r') as file:
            data = file.read()
    else:
        with open("ruolo_classic.txt", 'r') as file:
            data = file.read()

    chat_id = update.message.chat_id
    bot.send_message(chat_id=chat_id, text=data)


def refresh(bot, update):
    """Define the /refresh command behaviour"""
    chatID = update.message.chat_id
    chosen_ids = chosen_dict[chatID]
    for key, _ in chosen_ids.items():
        chosen_ids[key].clear()
    bot.send_message(chat_id=chatID, text="Refresh effettuato")


def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('cat', cat))
    dp.add_handler(CommandHandler('dog', dog))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('nomesquadra', nomesquadra))
    dp.add_handler(CommandHandler('ruolo', ruolo))
    dp.add_handler(CommandHandler('progress', progress))
    dp.add_handler(CommandHandler('refresh', refresh))
    dp.add_handler(CommandHandler('classic', classic))
    dp.add_handler(CommandHandler('mantra', mantra))
    

    for i, squad in enumerate(get_squads(url_squads)):
        """Creates a command for each team with its name"""
        dp.add_handler(CommandHandler(squad, get_squad_function(i)))

    for role in set(roles.values()):
        """Creates a command for each role with its name"""
        dp.add_handler(CommandHandler(role, get_role_function(role)))

    get_players_url()

    for name in get_players_name():
        """Creates a command for each player with his name"""
        dp.add_handler(CommandHandler(name, get_player_info_function(name)))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
    