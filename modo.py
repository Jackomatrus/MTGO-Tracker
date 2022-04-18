# MODO GameLog Cleaning Module
import copy
from time import strftime, struct_time
from typing import Literal, Union
import re
from MODO_DATA import (
    BASIC_LAND_DICT, CARDS_DRAWN_DICT, CONSTRUCTED_FORMATS, CONSTRUCTED_PLAY_TYPES, 
    CUBE_FORMATS, DRAFT_FORMATS, DRAFT_PLAY_TYPES, LIMITED_FORMATS, HEADERS,
    ADVENTURE_CARDS, SEALED_FORMATS, SEALED_PLAY_TYPES, SPLIT_CARDS, MULL_DICT
    )

# To add a column to a database:
# Add the column to MODO_DATA.HEADERS dict.
# Add the column to appropriate modo.XXXX_data() function.
# Any saved data will have to be deleted and reloaded.

# To add a menu option to dropdowns in revision windows:
# Add the option to the appropriate list below.
# Add the option under the appropriate header in the input_options.txt file.

def clean_card_set(card_set: set[str]) -> set[str]:
    """Fixes sets of adventure and split card names for draft.

    Args:
        card_set (set[str]): A set of card names.

    Returns:
        set[str]: Modified set (removed NA values and fixed split/adv)
    """
    for i in list(card_set):
        if i == "NA":
            card_set.remove(i)
        elif i in SPLIT_CARDS:
            card_set.add(SPLIT_CARDS[i])
            card_set.remove(i)
        elif i in ADVENTURE_CARDS:
            card_set.add(ADVENTURE_CARDS[i])
            card_set.remove(i)
    return card_set

def invert_join(ad):
    # Input:  List[List[Matches],List[Games],List[Plays]]
    # Output: List[List[Matches],List[Games],List[Plays]]

    def swap_cols(data,header,col_a,col_b):

        # Input:  List[Matches or Games],List[Headers],String,String
        # Output: List[Matches]   

        for index,i in enumerate(header):
            if i == col_a:
                a = index
            elif i == col_b:
                b = index
        data[a], data[b] = data[b], data[a]

    def invert_matchdata(data):
        # Input:  List[Matches]
        # Output: List[Matches]

        swap_cols(data,HEADERS['Matches'],"P1","P2")
        swap_cols(data,HEADERS['Matches'],"P1_Arch","P2_Arch")
        swap_cols(data,HEADERS['Matches'],"P1_Subarch","P2_Subarch")
        swap_cols(data,HEADERS['Matches'],"P1_Roll","P2_Roll")
        swap_cols(data,HEADERS['Matches'],"P1_Wins","P2_Wins")

        cols_to_invert = ["Match_Winner","Roll_Winner"]
        for i in cols_to_invert:
            for index,j in enumerate(HEADERS['Matches']):
                if j == i:
                    a = index
            if data[a] == "P1":
                data[a] = "P2"
            elif data[a] == "P2":
                data[a] = "P1"

    def invert_gamedata(data):
        # Input:  List[Games]
        # Output: List[Games]

        swap_cols(data,HEADERS["Games"],"P1","P2")
        swap_cols(data,HEADERS["Games"],"P1_Mulls","P2_Mulls")
        swap_cols(data,HEADERS["Games"],"On_Play","On_Draw")
        
        cols_to_invert = ["PD_Selector","Game_Winner"]
        for i in cols_to_invert:
            for index,j in enumerate(HEADERS["Games"]):
                if j == i:
                    a = index
            if data[a] == "P1":
                data[a] = "P2"
            elif data[a] == "P2":
                data[a] = "P1"

    ad_inverted = copy.deepcopy(ad)
    for i in ad_inverted[0]:
        invert_matchdata(i)
    for i in ad_inverted[1]:
        invert_gamedata(i)

    ad_inverted[0] += ad[0]
    ad_inverted[1] += ad[1]

    return ad_inverted
def update_game_wins(ad,timeout):
    #Input:  List[Matches,Games,Plays]
    #Output: List[Matches,Games,Plays]
    
    p1_index = HEADERS['Matches'].index("P1")
    p2_index = HEADERS['Matches'].index("P2")
    p1wins_index = HEADERS['Matches'].index("P1_Wins")
    p2wins_index = HEADERS['Matches'].index("P2_Wins")
    mw_index = HEADERS['Matches'].index("Match_Winner")
    gw_index = HEADERS["Games"].index("Game_Winner")

    for i in ad[0]: # Iterate through Matches.
        i[p1wins_index] = 0
        i[p2wins_index] = 0
        i[mw_index]     = "NA"
        for j in ad[1]: # Iterate through Games.
            if i[0] == j[0]: # If Match and Game have matching Match_ID
                if j[gw_index] == "P1": # Check if P1 or P2 won the game.
                    i[p1wins_index] += 1
                elif j[gw_index] == "P2":
                    i[p2wins_index] += 1
                elif j[gw_index] == "NA":
                    pass
        if i[p1wins_index] > i[p2wins_index]:
            i[mw_index] = "P1"
        elif i[p2wins_index] > i[p1wins_index]:
            i[mw_index] = "P2"
        else:
            if i[0] in timeout:
                if i[p1_index] == timeout[i[0]]:
                    i[mw_index] = "P2"
                elif i[p2_index] == timeout[i[0]]:
                    i[mw_index] = "P1"
def players(game_log: Union[str, list[str]]) -> list[str]:
    """Parses a gamelog for player names.

    Args:
        init (Union[str, list[str]]): The pure game log.

    Returns:
        list[str]: all player names
    """

    if isinstance(game_log, str):
        player_name_re = re.compile( r'@P@P(.+?) joined the game\.')
        # alternative: r'@P(?!.*?@P.{0,30} join)(.+?) joined the game\.'
    elif isinstance(game_log, list):
        game_log = '\n'.join(game_log)
        player_name_re = re.compile(r'^(.*?) joined the game', re.MULTILINE)
    else:
        raise TypeError(f"Expected log as list of strings or string,"
                        f"got {type(game_log)}")
    # remove duplicates
    players = list(set(player_name_re.findall(game_log)))
    players.sort(key=len, reverse=True) # not sure why sorting
    return players

def alter(player_name: str, original: bool) -> str:
    """If original: replaces + -> " " and * -> .
        Otherwise reverses these operations.
        Used to prevent errors with str.split during parsing.

    Args:
        player_name (str): The player name
        original (bool): Set to True if you need the real name.
            Set to False if you need a prettyfied name for parsing.

    Returns:
        str: Replaced string
    """
    if original:
        player = player_name.replace("+"," ")
        player = player.replace("*",".")
    else:
        player = player_name.replace(" ","+")
        player = player.replace(".","*")
    return player
def closest_list(
    cards_played: set[str],
    ad: dict[str, tuple[str, str, set[str]]],
    yyyy_mm: str) -> tuple[str, str]:
    
    decks = []
    yyyy = yyyy_mm[0:4]
    mm = yyyy_mm[5:7]
    if mm == "01":
        mm = "12"
        yyyy = str(int(yyyy) - 1)
    else:
        mm = str(int(mm) - 1).zfill(2)
    yyyy_mm_prev = yyyy + "-" + mm

    if yyyy_mm in ad:
        decks = ad.get(yyyy_mm).copy()
    if yyyy_mm_prev in ad:
        decks.extend(ad.get(yyyy_mm_prev).copy())
    if decks == []:
        return ["Unknown","NA"]

    similarity_list = []
    for i in decks:
        if i == None:
            print("error: Null List")
            continue

        if len(i[2]) == 0:
            similarity = 0
        else:
            similarity = len(cards_played.intersection(i[2]))/len(i[2])
        similarity = round((similarity * 100),3)
        similarity_list.append(similarity)

    index = similarity_list.index(max(similarity_list))
    if max(similarity_list) > 20:
        return [decks[index][0],decks[index][1]]
    else:
        return ["Unknown","NA"]
def get_limited_subarch(cards_played: set[str]) -> Union[str, Literal["NA"]]:
    """Names the sub-archetype after the basic lands played.

    Args:
        cards_played (set[str]): Set of strings representing played cards.

    Returns:
        str: A slice of "WUBRG" or "NA"
    """

    sub_archetype = ''
    for basic, color in BASIC_LAND_DICT.items():
        if basic in cards_played:
            sub_archetype += color
    if not sub_archetype:
        return "NA"
    else:
        return sub_archetype

def parse_list(filename: str, file_content: str) -> tuple[str, str, set[str]]:
    """Reads out a decklist from strings.

    Args:
        filename (str): File name of format "Format - Deckname.txt"
        file_content (str): Cards in the deck.
            Sideboard seperated by blank line.
            Format: \d+ Cardname

    Returns:
        tuple[str, str, set[str]]: _description_
    """

    filename_re = re.compile(r'(.+) - (.+)\.txt')
    deck_format, deck_name = filename_re.findall(filename)[0]
    maindeck = []
    sideboard = []
    target = maindeck

    for line in file_content.split("\n"):
        if line == "":
            # sideboard comes after empty line, everything before is main
            target = sideboard
        else:
            card_count, card = line.split(" ",1)
            target.extend((card,) * int(card_count))
    return (deck_name,deck_format,set(maindeck))

def check_timeout(ga: list[str]) -> tuple[bool, Union[Literal[None], str]]:
    """Checks whether a player has timed out in a list of game actions.

    Args:
        ga (list[str]): List of game actions

    Returns:
        tuple[bool, Union[Literal[None], str]]: 
        Boolean value is whether someone timed out.
        If someone timed out, string is the players name.
    """
    for i in ga:
        if " has lost the game due to disconnection" in i:
            return (True,i.split(" has lost the game due to disconnection")[0])
        # added timeout without disconnect
        elif " has run out of time and has lost the match" in i:
            return (True,i.split(" has run out of time and has lost the match")[0])
    return (False,None)

def game_actions(game_log: str, file_modified_time: struct_time) -> list[str]:
    # Input:  String,String
    # Output: List[Strings]
    game_actions = []
    players_list = players(game_log)
    lost_conn = False
    turn_header = re.compile(r"Turn \d+: ")

    for i in players_list:
        game_log = game_log.replace(i,alter(i,original=False))
    # skip all text up to first @P
    game_log_list = game_log.split("@P")[1:]
    game_actions.append(strftime(r'%Y%m%d%H%M', file_modified_time))
    for i in game_log_list:
        fullstring = i.replace(" (Alt.)", "")
        fullstring = fullstring.split(".")[0]
        # Player joined game header.
        if " has lost connection to the game" in i:
            lost_conn = True
        elif " joined the game." in i:
            if lost_conn:
                lost_conn = False
            else:
                game_actions.append(fullstring)
        # Skip looking at extra cards.
        elif " draws their next card." in i:
            continue
        # Skip leaving to sideboard.
        elif " has left the game." in i:
            continue
        # New turn header. Removes the artifacts
        elif turn_header.search(i):
            newstring = " ".join(i.split()[0:2])
            for j in players_list:
                if len(newstring.split()) < 3: # <-- this seems to always be true??
                    if alter(j,original=False) in i.split(": ")[1]:
                        newstring += " " + alter(j,original=False)
            game_actions.append(newstring)
        # Skip game state changes.
        elif ('.' not in i) and ("is being attacked" not in i):
            continue
        
        elif ("@[" in fullstring) and ("@]" in fullstring):
            # changes every @[Cardname@:NUMBERS,NUMBERS:@] to @[Cardname@]
            newstring = re.sub(
                r"(@\[.+?)(@:\d+?,\d+?:)(@\])", 
                r'\g<1>\g<3>', # remove group 2
                fullstring)
            newstring = newstring.split("(")[0] # not sure why this is here
            game_actions.append(newstring)
        # Everything else
        elif "." in i:
            game_actions.append(fullstring)
    return game_actions


def high_roll(init: Union[str, list[str]]) -> dict:
    remove_trailing = False
    if isinstance(init, str):
        init = init.split("@P")
        remove_trailing = True
    rolls = {}
    for i in init:
        if remove_trailing:
            tstring = i.rsplit(".",1)[0]
        else:
            tstring = i
        if " rolled a " in i:
            tlist = tstring.split(" rolled a ")
            if len(tlist[1]) == 1:
                rolls[tlist[0].replace(" ","+")] = int(tlist[1])
    return rolls

def match_data(ga,gd,pd):
    # Input:  List[GameActions],List[GameData],List[PlayData]
    # Output: List[Match_Attributes]

    MATCH_DATA =    []
    P1 =            players(ga)[0]
    P1_ARCH =       "NA"
    P1_SUBARCH =    "NA"
    P2 =            players(ga)[1]
    P2_ARCH =       "NA"
    P2_SUBARCH =    "NA"
    try:
        P1_ROLL =       high_roll(ga)[P1]
        P2_ROLL =       high_roll(ga)[P2]
    except KeyError:
        print('oh no')
        return "High Rolls not Found."
    P1_WINS =       0
    P2_WINS =       0
    MATCH_WINNER =  ""
    MATCH_FORMAT =  "NA"
    LIM_FORMAT =    "NA"
    MATCH_TYPE =    "NA"
    DATE =          f"{ga[0][0:4]}-{ga[0][4:6]}-{ga[0][6:8]}-{ga[0][8:10]}:{ga[0][10:]}"
    MATCH_ID =      f"{ga[0]}_{P1}_{P2}"
    DRAFT_ID =      "NA"

    player_count =  len(players(ga))
    prev_string =   ""

    if P1_ROLL > P2_ROLL:
        ROLL_WINNER = "P1"
    else:
        ROLL_WINNER = "P2"
    
    for i in gd:
        if i[0] == MATCH_ID and i[HEADERS["Games"].index("Game_Winner")] == "P1":
            P1_WINS += 1
        elif i[0] == MATCH_ID and i[HEADERS["Games"].index("Game_Winner")] == "P2":
            P2_WINS += 1

    if P1_WINS > P2_WINS:
        MATCH_WINNER = "P1"
    elif P2_WINS > P1_WINS:
        MATCH_WINNER = "P2"
    else:
        timeout = check_timeout(ga)
        if timeout[0] == True:
            if timeout[1] == P1:
                MATCH_WINNER = "P2"
            else:
                MATCH_WINNER = "P1"
        else:
            MATCH_WINNER = "NA"

    MATCH_DATA.extend((
        MATCH_ID,
        DRAFT_ID,
        alter(P1,original=True),
        P1_ARCH,
        P1_SUBARCH,
        alter(P2,original=True),
        P2_ARCH,
        P2_SUBARCH,
        P1_ROLL,
        P2_ROLL,
        ROLL_WINNER,
        P1_WINS,
        P2_WINS,
        MATCH_WINNER,
        MATCH_FORMAT,
        LIM_FORMAT,
        MATCH_TYPE,
        DATE))
    return MATCH_DATA

def get_winner(curr_game_list: list[str], p1: str, p2: str
    ) -> Union[Literal["NA"], Literal["P1"], Literal["P2"]]:
    # definitive loss statements
    LOSE_SENTENCES = (
        "has lost the game", 
        "loses because of drawing a card",
        "has conceded"
    )
    for loss_reason in LOSE_SENTENCES:
        for action in curr_game_list:
            # concession
            if loss_reason in action:
                if action.startswith(p1):
                    return "P2"
                elif action.startswith(p2):
                    return "P1"

    lastline = curr_game_list[-1]
    # Last game actions that imply a loss
    MAYBE_LOSS_SENTENCES = (
        "is being attacked"
    )
    # Last game actions that imply a win
    WIN_SENTENCES = (
        "triggered ability from [Thassa's Oracle]",
        'casts [Approach of the Second Sun]'
    )
    # if the final line contains one of the above
    if any(s in lastline for s in MAYBE_LOSS_SENTENCES):
        if lastline.startswith(p1):
            return "P2"
        elif lastline.startswith(p2):
            return "P1"
    # if the final line contains any win statements
    elif any(s in lastline for s in WIN_SENTENCES):
        if lastline.startswith(p1):
            return "P1"
        elif lastline.startswith(p2):
            return "P2"
    # Could not determine a winner.
    else:
        return "NA"


def game_data(ga):
    # Input:  List[GameActions]
    # Output: List[G1_List,G2_List,G3_List,NA_Games_Dict{}]

    GAME_DATA =     []
    G1 =            []
    G2 =            []
    G3 =            []    
    ALL_GAMES_GA =  {}

    GAME_NUM =      0
    PD_SELECTOR =   ""
    PD_CHOICE =     ""
    ON_PLAY =       ""
    ON_DRAW =       ""
    P1_MULLS =      0
    P2_MULLS =      0
    TURNS =         0
    GAME_WINNER =   ""

    try:
        P1 =            players(ga)[0]
        P2 =            players(ga)[1]
    except IndexError:
        return "Players not Found."
    curr_game_list =[]
    player_count =  len(players(ga))
    prev_string =   ""
    curr_list =     []
    MATCH_ID = f"{ga[0]}_{P1}_{P2}"

    for i in ga:
        curr_list = i.split()
        if "joined the game" in i:
            if player_count == 0:
                # New Game
                player_count = len(players(ga)) - 1
                GAME_WINNER = get_winner(curr_game_list,P1,P2)
                if GAME_WINNER == "NA":
                    ALL_GAMES_GA[f"{MATCH_ID}-{GAME_NUM}"] = curr_game_list
                if GAME_NUM == 1:
                    G1.extend((
                        MATCH_ID,
                        alter(P1,original=True),
                        alter(P2,original=True),
                        GAME_NUM,
                        PD_SELECTOR,
                        PD_CHOICE,
                        ON_PLAY,
                        ON_DRAW,
                        P1_MULLS,
                        P2_MULLS,
                        TURNS,
                        GAME_WINNER))
                    GAME_DATA.append(G1)
                elif GAME_NUM == 2:
                    G2.extend((
                        MATCH_ID,
                        alter(P1,original=True),
                        alter(P2,original=True),
                        GAME_NUM,
                        PD_SELECTOR,
                        PD_CHOICE,
                        ON_PLAY,
                        ON_DRAW,
                        P1_MULLS,
                        P2_MULLS,
                        TURNS,
                        GAME_WINNER))
                    GAME_DATA.append(G2)
                curr_game_list = []
            else:
                player_count -= 1
        elif "chooses to play first" in i or "chooses to not play first" in i:
            GAME_NUM += 1
            if curr_list[0] == P1:
                PD_SELECTOR = "P1"
            else:
                PD_SELECTOR = "P2"
            if curr_list[3] == "play":
                PD_CHOICE = "Play"
            else:
                PD_CHOICE = "Draw"
            if PD_SELECTOR == "P1" and PD_CHOICE == "Play":
                ON_PLAY = "P1"
                ON_DRAW = "P2"
            elif PD_SELECTOR == "P2" and PD_CHOICE == "Play":
                ON_PLAY = "P2"
                ON_DRAW = "P1"
            elif PD_SELECTOR == "P1" and PD_CHOICE == "Draw":
                ON_PLAY = "P2"
                ON_DRAW = "P1"
            elif PD_SELECTOR == "P2" and PD_CHOICE == "Draw":
                ON_PLAY = "P1"
                ON_DRAW = "P2"
        elif "begins the game with" in i and "cards in hand" in i:
            if P1 == curr_list[0]:              
                P1_MULLS = MULL_DICT[i.split(" begins the game with ")[1].split()[0]]
            elif P2 == curr_list[0]:
                P2_MULLS = MULL_DICT[i.split(" begins the game with ")[1].split()[0]]
        elif "Turn " in i and len(curr_list) == 3:
            TURNS = int(curr_list[1].split(":")[0])
        curr_game_list.append(i)
    GAME_WINNER = get_winner(curr_game_list,P1,P2)
    if GAME_WINNER == "NA":
        ALL_GAMES_GA[f"{MATCH_ID}-{GAME_NUM}"] = curr_game_list
    if GAME_NUM == 1:
        G1.extend((
            MATCH_ID,
            alter(P1,original=True),
            alter(P2,original=True),
            GAME_NUM,
            PD_SELECTOR,
            PD_CHOICE,
            ON_PLAY,
            ON_DRAW,
            P1_MULLS,
            P2_MULLS,
            TURNS,
            GAME_WINNER))
        GAME_DATA.append(G1)
    elif GAME_NUM == 2:
        G2.extend((
            MATCH_ID,
            alter(P1,original=True),
            alter(P2,original=True),
            GAME_NUM,
            PD_SELECTOR,
            PD_CHOICE,
            ON_PLAY,
            ON_DRAW,
            P1_MULLS,
            P2_MULLS,
            TURNS,
            GAME_WINNER))
        GAME_DATA.append(G2)
    elif GAME_NUM == 3:
        G3.extend((
            MATCH_ID,
            alter(P1,original=True),
            alter(P2,original=True),
            GAME_NUM,
            PD_SELECTOR,
            PD_CHOICE,
            ON_PLAY,
            ON_DRAW,
            P1_MULLS,
            P2_MULLS,
            TURNS,
            GAME_WINNER))
        GAME_DATA.append(G3)
    return (GAME_DATA,ALL_GAMES_GA)

def is_play(play: str) -> bool:
    action_keywords = ["plays","casts","draws","chooses","discards"]
    action_keyphrases = [
        "is being attacked by",
        "puts triggered ability from",
        "activates an ability of",]
    curr_list = play.split()
    if len(curr_list) > 1:
        for i in action_keyphrases:
            if i in play:
                return True
        if curr_list[1] in action_keywords:
            return True
    return False

def get_cards(play: str) -> list[str]:
    card_re = re.compile(r"@\[(.+?)@]")
    """old code
    cards = []
    count = play.count("@[")
    while count > 0:
        play = play.split("@[",1)
        play = play[1].split("@]",1)
        cards.append(play[0])
        play = play[1]
        count -= 1  
    """
    return card_re.findall(play)

def play_data(ga: list[str]):
    # Input:  List[GameActions]
    # Output: List[Plays]

    def player_is_target(
        tstring: str, player: str
        ) -> Union[Literal[0], Literal[1]]:
        while tstring.count("[") > 0:
            tstring = tstring.split("[",1)
            if player in tstring[0]:
                return 1
            else:
                tstring = tstring[1].split("]",1)[1]
        if player in tstring:
            return 1   
        return 0

    PLAY_DATA = []
    ALL_PLAYS = []

    GAME_NUM = 0
    PLAY_NUM = 0
    TURN_NUM = 0
    ACTIVE_PLAYER = ""
    NON_ACTIVE_PLAYER = ""

    P1 = players(ga)[0]
    P2 = players(ga)[1]
    MATCH_ID = f"{ga[0]}_{P1}_{P2}"

    for i in ga:
        curr_list = i.split()
        CASTING_PLAYER = ""
        ACTION = ""
        PRIMARY_CARD = "NA"
        TARGET_1 = "NA"
        TARGET_2 = "NA"
        TARGET_3 = "NA"
        OPP_TARGET = 0
        SELF_TARGET = 0
        CARDS_DRAWN = 0
        ATTACKERS = 0
        PLAY_DATA = []
        if (i.find("chooses to play first") != -1) or (i.find("chooses to not play first") != -1):
            GAME_NUM += 1
            PLAY_NUM = 0
        elif (i.find("Turn ") != -1) and (len(curr_list) == 3):
            TURN_NUM = int(curr_list[1].split(":")[0])
            ACTIVE_PLAYER = curr_list[2]
            if ACTIVE_PLAYER == P1:
                NON_ACTIVE_PLAYER = P2
            else:
                NON_ACTIVE_PLAYER = P1
        elif is_play(i):
            if curr_list[1] == "plays":
                CASTING_PLAYER = curr_list[0]
                try:
                    PRIMARY_CARD = get_cards(i)[0]
                # MODO Bug Encountered. Primary_Card = "NA"
                except IndexError:
                    pass
                ACTION = "Land Drop"
            elif curr_list[1] == "casts":
                CASTING_PLAYER = curr_list[0]
                try:
                    PRIMARY_CARD = get_cards(i)[0]
                # MODO Bug Encountered. Primary_Card = "NA"
                except IndexError:
                    pass
                ACTION = curr_list[1].capitalize()
                if i.find("targeting") != -1:
                    targets = get_cards(i.split("targeting")[1])
                    try:
                        TARGET_1 = targets[0]
                    except IndexError:
                        pass
                    try:
                        TARGET_2 = targets[1]
                    except IndexError:
                        pass
                    try:
                        TARGET_3 = targets[2]
                    except IndexError:
                        pass
                    if CASTING_PLAYER == P1:
                        SELF_TARGET = player_is_target(i.split("targeting")[1],P1)
                        OPP_TARGET = player_is_target(i.split("targeting")[1],P2)
                    elif CASTING_PLAYER == P2:
                        SELF_TARGET = player_is_target(i.split("targeting")[1],P2)
                        OPP_TARGET = player_is_target(i.split("targeting")[1],P1)                    
            elif curr_list[1] == "draws":
                CASTING_PLAYER = curr_list[0]
                ACTION = curr_list[1].capitalize()
                CARDS_DRAWN = CARDS_DRAWN_DICT.get(curr_list[2], 8)
            elif curr_list[1] == "chooses":
                continue
            elif curr_list[1] == "discards":
                continue
            elif i.find("is being attacked by") != -1:
                CASTING_PLAYER = ACTIVE_PLAYER
                ACTION = "Attacks"
                ATTACKERS = len(get_cards(i.split("is being attacked by")[1]))
            elif i.find("puts triggered ability from") != -1:
                CASTING_PLAYER = curr_list[0]
                try:
                    PRIMARY_CARD = get_cards(i)[0]
                except IndexError:
                    PRIMARY_CARD = i.split("triggered ability from ")[1].split(" onto the stack ")[0]
                    # MODO Bug Encountered. Primary_Card = "NA"
                    if (PRIMARY_CARD == P1) or (PRIMARY_CARD == P2):
                        PRIMARY_CARD = "NA"
                ACTION = "Triggers"
                if i.find("targeting") != -1:
                    targets = get_cards(i.split("targeting")[1])
                    try:
                        TARGET_1 = targets[0]
                    except IndexError:
                        pass
                    try:
                        TARGET_2 = targets[1]
                    except IndexError:
                        pass
                    try:
                        TARGET_3 = targets[2]
                    except IndexError:
                        pass
                    if CASTING_PLAYER == P1:
                        SELF_TARGET = player_is_target(i.split("targeting")[1],P1)
                        OPP_TARGET = player_is_target(i.split("targeting")[1],P2)
                    elif CASTING_PLAYER == P2:
                        SELF_TARGET = player_is_target(i.split("targeting")[1],P2)
                        OPP_TARGET = player_is_target(i.split("targeting")[1],P1)
            elif i.find("activates an ability of") != -1:
                CASTING_PLAYER = curr_list[0]
                try:
                    PRIMARY_CARD = get_cards(i)[0]
                except IndexError:
                    PRIMARY_CARD = i.split("activates an ability of ")[1].split(" (")[0]
                    # MODO Bug Encountered. Primary_Card = "NA"
                    if (PRIMARY_CARD == P1) or (PRIMARY_CARD == P2):
                        PRIMARY_CARD = "NA"
                ACTION = "Activated Ability"
                if i.find("targeting") != -1:
                    targets = get_cards(i.split("targeting")[1])
                    try:
                        TARGET_1 = targets[0]
                    except IndexError:
                        pass
                    try:
                        TARGET_2 = targets[1]
                    except IndexError:
                        pass
                    try:
                        TARGET_3 = targets[2]
                    except IndexError:
                        pass
                    if CASTING_PLAYER == P1:
                        SELF_TARGET = player_is_target(i.split("targeting")[1],P1)
                        OPP_TARGET = player_is_target(i.split("targeting")[1],P2)
                    elif CASTING_PLAYER == P2:
                        SELF_TARGET = player_is_target(i.split("targeting")[1],P2)
                        OPP_TARGET = player_is_target(i.split("targeting")[1],P1)
            PLAY_NUM += 1
            PLAY_DATA.extend((
                MATCH_ID,
                GAME_NUM,
                PLAY_NUM,
                TURN_NUM,
                alter(CASTING_PLAYER,original=True),
                ACTION,
                PRIMARY_CARD,
                TARGET_1,
                TARGET_2,
                TARGET_3,
                OPP_TARGET,
                SELF_TARGET,
                CARDS_DRAWN,
                ATTACKERS,
                alter(ACTIVE_PLAYER,original=True),
                alter(NON_ACTIVE_PLAYER,original=True)))
            ALL_PLAYS.append(PLAY_DATA)
    return ALL_PLAYS

def get_all_data(game_log: str, file_last_modified: struct_time):
    # Input:  String,String
    # Output: List[Matches,Games,Plays]
    
    gameactions = game_actions(game_log,file_last_modified)
    gamedata = game_data(gameactions)
    if isinstance(gamedata, str):
        return gamedata
    playdata = play_data(gameactions)
    matchdata = match_data(gameactions,gamedata[0],playdata)
    if isinstance(matchdata, str):
        return matchdata
    timeout = check_timeout(gameactions)

    return [matchdata,gamedata[0],playdata,gamedata[1],timeout]
