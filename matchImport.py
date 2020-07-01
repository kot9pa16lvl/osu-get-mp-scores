from __future__ import print_function
from oauth2client.service_account import ServiceAccountCredentials
import pickle
import os.path
import gspread
import urllib.request
from time import sleep

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


JSON_FILENAME = 'osu match-cost-4700d866f34f.json'
SLEEP_TIME = 10
SAMPLE_SPREADSHEET_ID = '16IQmSZcA9vdYGUWX1ywYVD4bC3Yx01kKCnDtq9MJblY' #cfg
'''
WORKSHEET_NAME = input("Введите название вкладки дока: ") #input
mp_link = input("Введите мп линк: ") #input
'''



def exec_cfg():
    global JSON_FILENAME
    global SLEEP_TIME
    global SAMPLE_SPREADSHEET_ID
    cfg = open("config.txt", "r")
    for line in cfg.readlines():
        if (line.split(':')[0] == 'JSON_FILENAME'):
            JSON_FILENAME = ''.join(line.split(':')[1:]).rstrip()
        if (line.split(':')[0] == 'SLEEP_TIME'):
            SLEEP_TIME = int(''.join(line.split(':')[1:]).rstrip())
        if (line.split(':')[0] == 'SPREADSHEET_ID'):
            SAMPLE_SPREADSHEET_ID = ''.join(line.split(':')[1:]).rstrip()
def get_worksheet(mp_link, spreadsheet_id):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    '''
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

'''
    
    #gc = gspread.authorize(credentials=creds)
    gc = gspread.authorize(credentials=ServiceAccountCredentials.from_json_keyfile_name(JSON_FILENAME, SCOPES))
    worksheet = gc.open_by_key(spreadsheet_id)
    return worksheet



def get_beatmap_scores_order(mp_link):
    nicknames = dict()
    response = urllib.request.urlopen(mp_link)
    http_mp = response.read().decode('UTF-8')
    http_mp_split = http_mp.split(',')


    for i in range(len(http_mp_split)):
        #print(http_mp_split[i])
        elem = http_mp_split[i]
        if '"username":' in elem:
            #print(http_mp_split[i], http_mp_split[i - 1])
            nicknames[int(http_mp_split[i - 8].split(':')[-1])] = http_mp_split[i].split(':')[-1][1:-1]

    beatmap_scores = dict() #beatmap id -> list of [username, score, acc]
    cur_beatmap_id = 0
    cur_accuracy = 0
    cur_score = 0
    cur_user_id = 0
    beatmap_order = []
    for i in range(len(http_mp_split)):
        elem = http_mp_split[i]
        if '"beatmap":' in elem:
            #print(elem, http_mp_split[i - 1], http_mp_split[i - 2])
            cur_beatmap_id = int(http_mp_split[i + 1].split(':')[-1])
            if not (cur_beatmap_id in beatmap_scores):
                    beatmap_scores[cur_beatmap_id] = []
                    beatmap_order.append(cur_beatmap_id)
        if '"accuracy":' in elem:
           # print(elem, http_mp_split[i - 1])
            cur_accuracy = float(elem.split(':')[-1])
            cur_accuracy = round(cur_accuracy * 10000) / 100
            cur_user_id = int(http_mp_split[i - 1].split(':')[-1])
        if '"score":' in elem:
            cur_score = int(elem.split(':')[-1])
            fill_flag = True
            for j in range(len(beatmap_scores[cur_beatmap_id])):
                if beatmap_scores[cur_beatmap_id][j][0] == nicknames[cur_user_id]:
                    fill_flag = False
                    if (beatmap_scores[cur_beatmap_id][j][1] < cur_score):
                        beatmap_scores[cur_beatmap_id][j] = [nicknames[cur_user_id], cur_score, cur_accuracy]
            if fill_flag:
                beatmap_scores[cur_beatmap_id].append([nicknames[cur_user_id], cur_score, cur_accuracy])
    return beatmap_scores, beatmap_order

def get_beatmap_scores(mp_link):
    beatmap_scores, beatmap_order = get_beatmap_scores(mp_link)
    return beatmap_scores



def get_worksheet_id(worksheet, worksheet_name):
    worksheet_list = worksheet.worksheets()
    sheet_id = 0
    for i in range(len(worksheet_list)):
        if worksheet_name in str(worksheet_list[i]):
            return i

def low_case(string):
    ans = []
    for elem in string:
        if 65 <= ord(elem) <= 90:
            ans.append(chr(ord(elem) + 32))
        else:
            ans.append(elem)
    return (''.join(ans))

def get_difficulty_norm(worksheet):
    while True:
        try:
            for elem in worksheet.col_values(3):
                if low_case(elem) == 'easy':
                    return 600000
                if low_case(elem) == 'medium':
                    return 500000
                if low_case(elem) == 'hard':
                    return 400000
            break
        except:
            pass
    return 1000000 / 0


def get_beatmap_row(worksheet, beatmap_id):
    score_row = 0
    ids_row = worksheet.col_values(2)
    for row in range(1, len(ids_row) + 1):
        if ids_row[row - 1] == str(beatmap_id):
            score_row = row
    return score_row

def get_matchcost_row(worksheet):
    id_col = []
    while True:
        try:
            id_col = worksheet.col_values(2)
            break
        except:
            pass
    for i in range(len(id_col)):
        if (low_case(id_col[i])) == 'difficulty:':
            return i + 1

def get_last_player_col(worksheet):
    players = worksheet.row_values(2)
    if (players[-1] == 'Stage'):
        return len(players) + 1
    else:
        return len(players) + 2


def fill_scores(worksheet, beatmap_scores):
    fake_ids = []
    for beatmap_id in beatmap_scores:
        if get_beatmap_row(worksheet, beatmap_id) == 0:
            fake_ids.append(beatmap_id)
    for beatmap_id in fake_ids:
        beatmap_scores.pop(beatmap_id, None)
    update_progress("Filling nicknames")
    nicknames = set()
    for scores_id in beatmap_scores:
        for score in beatmap_scores[scores_id]:
            nicknames.add(score[0])
    nicknames = list(nicknames)
    user_column = dict() #nickname -> column

    begin = get_last_player_col(worksheet)
    for i in range(begin, begin + len(nicknames) * 2, 2):
        while True:
            try:
                worksheet.update_cell(2, i, nicknames[(i - begin) // 2])
                break
            except:
                pass
        user_column[nicknames[(i - begin) // 2]] = i
    sleep(SLEEP_TIME)
    update_progress("Filling match cost")
    user_scores = dict() #username -> his scores
    for beatmap_id in beatmap_scores:
        for score in beatmap_scores[beatmap_id]:
            if score[0] in user_scores:
                user_scores[score[0]].append(score[1])
            else:
                user_scores[score[0]] = []
                user_scores[score[0]].append(score[1])

    user_costs = dict()
    
    difficulty_norm = get_difficulty_norm(worksheet)
    match_cost_row = get_matchcost_row(worksheet)
    for username in user_scores:
        #print(match_cost_row, user_column[username], sum(user_scores[username]) / len(user_scores[username]) / difficulty_norm)
        match_cost = sum(user_scores[username]) / len(user_scores[username]) / difficulty_norm
        match_cost = round(match_cost * 1000) / 1000
        user_costs[username] = match_cost
        while True:
            try:
                worksheet.update_cell(match_cost_row, user_column[username], match_cost)
                break
            except:
                pass
    sleep(SLEEP_TIME)

    beatmap_count = 0
    map_ids = worksheet.col_values(2)
    for beatmap_id in beatmap_scores:
        beatmap_count += 1
        score_row = get_beatmap_row(worksheet, beatmap_id)
        update_progress("Filling beatmap scores\nBeatmap: " + str(beatmap_id) +
                        " (" + str(beatmap_count) + " of " + str(len(beatmap_scores)) + ")")
        for score in beatmap_scores[beatmap_id]:
            #print(score, score_row, beatmap_id)
            column = user_column[score[0]]
            player_score = score[1]
            player_accuracy = score[2]
            while True:
                try:
                    worksheet.update_cell(score_row, column, player_score)
                    break
                except:
                    pass
            while True:
                try:
                    worksheet.update_cell(score_row, column + 1, player_accuracy)
                    break
                except:
                    pass
        sleep(SLEEP_TIME)
    
    return user_costs
    

def print_player_scores(beatmap_scores, order):
    #order = [2167561, 1042623, 2006067, 2347615, 2011421, 244234, 2150485,  1270701, 640211,  65019]
    nicknames = set()
    for scores_id in beatmap_scores:
        for score in beatmap_scores[scores_id]:
            nicknames.add(score[0])
    nicknames = list(nicknames)
    
    for nickname in nicknames:
        print(nickname)
        for map_id in order:
            isprt = False
            for score in beatmap_scores[map_id]:
                if (score[0] == nickname):
                    print(score[1])
                    isprt  = True
            if (not isprt):
                print("no score")
        print()
            

    #print(nicknaes)
def print_map_scores(beatmap_scores, order):
        #order = [2167561, 1042623, 2006067, 2347615, 2011421, 244234, 2150485,  1270701, 640211,  65019]
    nicknames = set()
    for scores_id in beatmap_scores:
        for score in beatmap_scores[scores_id]:
            nicknames.add(score[0])
    nicknames = list(nicknames)
    
    for beatmap_id in order:
        print("map -", beatmap_id)
        for player_scores in beatmap_scores[beatmap_id]:
            print("Player", player_scores[0], 'has', player_scores[1],  "score and ", player_scores[2],  "accuracy")
        print()


def fill_global_costs(worksheet, user_costs, week_name):
    player_row = worksheet.row_values(1)
    weeks_col = worksheet.col_values(1)
    print(week_name)
    user_col = dict()
    user_row = 0
    for username in user_costs:
        for i in range(len(player_row)):
            if player_row[i] == username:
                user_col[username] = i + 1

    for i in range(len(weeks_col)):
        if weeks_col[i] == week_name:
            user_row = i + 1
    print(user_costs)
    print(user_col)
    print(user_row)
    
    for username in user_col:
        worksheet.update_cell(user_row, user_col[username], user_costs[username])

    


exec_cfg()
'''



'''

from tkinter import *
from PIL import Image, ImageTk
root = Tk()
canv = Canvas(root, width=250, height=250, background='white')

canv.pack()

def create_bg():
    load = Image.open("bg.png")
    render = ImageTk.PhotoImage(load)
    img = Label(root, image=render)
    img.image = render
    img.place(x=0, y=0)

'''
def getSquareRoot ():  
    x1 = entry1.get()
    
    label = Label(root, text= float(x1)**0.5)
    canv.create_window(200, 230, window=label)
'''

def update_progress(text):
    global progress_text
    #canv.delete('result')
    #cur = canv.create_text(100, 200, text=text, fill='white', font="Andy 14", tag = 'result')
    progress_text.set(text)
    #cur.place(x=200, y=100, bordermode=OUTSIDE, height=30, width=70)
    

def fill_doc(sheet_name_entry, mp_link_entry):
    '''
    worksheet_name = sheet_name_entry.get()
    update_progress("Getting worksheet")
    worksheet_global = get_worksheet(mp_link, SAMPLE_SPREADSHEET_ID)
    update_progress("Getting scores")
    beatmap_scores = get_beatmap_scores(mp_link)
    worksheet = worksheet_global.get_worksheet(get_worksheet_id(worksheet_global, worksheet_name))
    user_costs = fill_scores(worksheet, beatmap_scores)
    worksheet_costs = worksheet_global.get_worksheet(get_worksheet_id(worksheet_global, "TEST"))
    fill_global_costs(worksheet_costs, user_costs, worksheet_name)
    '''
    mp_link = mp_link_entry.get()

    beatmap_scores, beatmap_order = get_beatmap_scores_order(mp_link)
    
    
    print_player_scores(beatmap_scores, beatmap_order)
    print_map_scores(beatmap_scores, beatmap_order)
    
def foo():
    pass

create_bg()
mp_link_entry = Entry(root) 
mp_link_window = canv.create_window(185, 40, window=mp_link_entry)
sheet_name_entry = Entry(root)
sheet_name_window = canv.create_window(185, 60, window=sheet_name_entry)
#canv.create_text(90, 40, text = "mp link", font="Andy 12", fill='black')
fill_button = Button(root, height=10, width=10, text="Fill scores", 
                    command=lambda: fill_doc(sheet_name_entry, mp_link_entry))
fill_button.place(x=150, y=80, bordermode=OUTSIDE, height=30, width=70)

progress_text = StringVar()
progress_button = Button(root, height=30, width=100, textvariable=progress_text, font = "Andy 15",
                    command=lambda: foo())
#progress_button.place(x=50, y=140, bordermode=OUTSIDE, height=50, width=150)

root.mainloop()
