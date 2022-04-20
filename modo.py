# MODO GameLog Cleaning Module
import copy
from time import strftime, struct_time, gmtime
from typing import Literal, Pattern, Union
import re
from MODO_DATA import (
    BASIC_LAND_DICT, CARDS_DRAWN_DICT, CONSTRUCTED_FORMATS, CONSTRUCTED_PLAY_TYPES, 
    CUBE_FORMATS, DRAFT_FORMATS, DRAFT_PLAY_TYPES, LIMITED_FORMATS, HEADERS,
    ADVENTURE_CARDS, COMMON_WORDS, SEALED_FORMATS, SEALED_PLAY_TYPES, SPLIT_CARDS, MULL_DICT
    )

# To add a column to a database:
# Add the column to MODO_DATA.HEADERS dict.
# Add the column to appropriate modo.XXXX_data() function.
# Any saved data will have to be deleted and reloaded.

# To add a menu option to dropdowns in revision windows:
# Add the option to the appropriate list below.
# Add the option under the appropriate header in the input_options.txt file.

# for future use maybe
class MatchActions(list):
    def __init__(self, *args):
        super(MatchActions, self).__init__(*args)
    
    @property
    def match_id(self):
        return self[0]

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

def alter(player_name: str, original: bool=False) -> str:
    """If original: replaces + -> " " and * -> .
        Otherwise reverses these operations.
        Used to prevent errors with str.split during parsing.

    Args:
        player_name (str): The player name
        original (bool): Set to True if you need the real name.
            Defaults to False to get a prettyfied name for parsing.

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
    # always returns in  WUBRG order because dicts are ordered as Python3.6
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
            # this works because list is mutable
            target = sideboard
        else:
            card_count, card = line.split(" ",1)
            target.extend((card,) * int(card_count))
    return (deck_name,deck_format,set(maindeck))

def check_timeout(
    game_actions: list[str]) -> tuple[bool, Union[Literal[None], str]]:
    """Checks whether a player has timed out in a list of game actions.

    Args:
        ga (list[str]): List of game actions

    Returns:
        tuple[bool, Union[Literal[None], str]]: 
        Boolean value is whether someone timed out.
        If someone timed out, string is the players name.
    """
    for action in game_actions:
        for reason in [
        " has lost the game due to disconnection",
        " has run out of time and has lost the match"]:
            if reason in action:
                player_name = action.split(reason)[0]
                return (True, player_name)
    return (False,None)

def remove_text_artifacts(game_action: str) -> str:
    """Tries to remove all text artifacts from the end of a string.

    Args:
        game_action (str): A game action string with artifacts at the end.

    Raises:
        ValueError: Only pass strings that you know to have artifacts.

    Returns:
        str: Same string but without the artifacts at the end.
            0.1% of the time there might remain a second '.' at the end.
    """
    # failsafe not to delete good data
    for word in COMMON_WORDS:
        if word in game_action[-10:]:
            raise ValueError('Expected string with text artifacts, got '
                f'"{game_action}"')
    # artifacts are at least 10 characters long
    game_action = game_action[:-10]
    # sometimes they're longer, try to catch
    if '.' in game_action[-4:-1]:
        game_action = game_action.rsplit('.', 1)[0]
    return game_action

def get_match_id(game_log: str) -> str:
    """Creates the match ID at the start of the game log.
        Match ids are started with $ and are 36 characters long.

    Args:
        game_log (str): String containing a match id as present in game logs.

    Returns:
        str: The match id without the $ sign, but with both player names added
            e.g. 36characterstring_Jackomatrus_Toffel
    """
    match_id_re = re.compile(r'\$([0-9a-zA-Z-]{36}).{1,2}\$\1')
    try:
        pure_id = match_id_re.findall(game_log)[0]
        player1, player2 = players(game_log)[0:2]
        return f'{pure_id}_{player1}_{player2}'
    except IndexError:
        raise ValueError(
            f'No match id in passed game log: {game_log}'
        )

def new_turn_regex(players: list[str]) -> re.Pattern:
    """Creates a regular expression that matches anything that looks like
        Turn X: PLAYERNAME

    Args:
        players (list[str]): List of names of players in the game.

    Returns:
        re.Pattern: The compiled regular expression
    """
    escaped_and_altered = [re.escape(alter(player)) for player in players]
    player_group_string = f"({'|'.join(escaped_and_altered)})"
    return re.compile(r'Turn (\d+): ' + player_group_string)

def all_actions(game_log: str) -> list[str]:
    # Input:  String
    # Output: List[Strings]
    all_action_list = [get_match_id(game_log)]
    players_list = players(game_log)
    turn_header = new_turn_regex(players_list)
    lost_conn = {player: False for player in players_list}
    for player in players_list:
        game_log = game_log.replace(player,alter(player))
    split_log = game_log.split("@P")
    game_log_list = [
        remove_text_artifacts(game_action) for game_action in split_log[1:-1]]
    # skip first entry, final entry doesn't have artifacts
    game_log_list.append(split_log[-1])
    for game_action in game_log_list:
        if not game_action:
            continue
        first_word = game_action.split()[0]
        turn_header_match = turn_header.search(game_action)
        if turn_header_match:
            # appends entire match 'Turn X: NAME'
            all_action_list.append(turn_header_match[0])
        elif " has lost connection to the game" in game_action:
            lost_conn[first_word] = True
        elif " joined the game." in game_action:
            if lost_conn[first_word]:
                # don't append reconnects
                lost_conn[first_word] = False
            else:
                # append regular joins
                all_action_list.append(game_action)
        # Skip any of these
        elif any(action in game_action for action in [
            " draws their next card.", # looking at extra cards
            " has left the game." ]): # sideboarding
            continue
        # Skip game state changes.
        elif ('.' not in game_action) and ("is being attacked" not in game_action):
            continue
        elif ("@[" in game_action) and ("@]" in game_action):
            # change every @[Cardname@:NUMBERS,NUMBERS:@] to @[Cardname@]
            newstring = re.sub(
                r"(@\[.+?)(@:\d+?,\d+?:)(@\])", 
                r'\g<1>\g<3>', # remove group 2
                game_action)
            all_action_list.append(newstring)
        # Everything else
        elif "." in game_action:
            all_action_list.append(game_action)
    return all_action_list

def high_roll(game_actions: Union[str, list[str]]) -> dict[str, int]:
    if isinstance(game_actions, str):
        game_actions = game_actions.split("@P")
    game_actions = '\n'.join(game_actions)
    roll_re = re.compile(r"^(.*?) rolled a ([1-6])", re.MULTILINE)
    rolls = {player: int(roll)
            for player, roll in roll_re.findall(game_actions)}
    return rolls

def match_data(ga,gd,pd):
    # Input:  List[GameActions],List[GameData],List[PlayData]
    # Output: List[Match_Attributes]

    MATCH_DATA =    []
    P1, P2 = players(ga)[0:2]
    P1_ARCH =       "NA"
    P1_SUBARCH =    "NA"
    P2_ARCH =       "NA"
    P2_SUBARCH =    "NA"
    try:
        rolls = high_roll(ga)
        P1_ROLL = rolls[P1]
        P2_ROLL = rolls[P2]
    except KeyError:
        raise ValueError(
            f"Game with players {players(ga)} doesn't have die rolls")
    P1_WINS =       0
    P2_WINS =       0
    MATCH_WINNER =  ""
    MATCH_FORMAT =  "NA"
    LIM_FORMAT =    "NA"
    MATCH_TYPE =    "NA"
    DATE =          "PLACEHOLDER THIS GETS REPLACED"
    MATCH_ID =      ga[0]
    DRAFT_ID =      "NA"

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
            if loss_reason in action:
                if action.startswith(p1):
                    return "P2"
                elif action.startswith(p2):
                    return "P1"

    lastline = curr_game_list[-1]
    # Last game actions that imply a loss
    MAYBE_LOSS_SENTENCES = (
        "is being attacked",
    )
    # Last game actions that imply a win
    WIN_SENTENCES = (
        "triggered ability from @[Thassa's Oracle@]",
        'casts @[Approach of the Second Sun@]'
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


def game_data(
    match_actions: list[str]
    ) -> tuple[
        list[list[str, int]], 
        dict[str, list[str]]
        ]:
    """Parses a list of actions in an entire match.

    Args:
        match_actions (list[str]): A list of actions provided from all_actions
            First entry in this list is the match_ID

    Returns:
        tuple[list[list[str, int]], dict[str, list[str]] ]: 
            A list of game lists and a dict of games without a winner.
            Each game list is structured 
            [Match_ID, P1, P2, game_num, pd_selector, pd_choice, on_play, 
            on_draw, P1_mulls, P2_mulls, num_turns, winner]
            Dict is structured {MatchID-GameNum: list[game actions]}
    """

    # needed variables
    ALL_PARSED_GAMES = []
    ALL_GAMES_GA = {}
    GAME_NUM = 0
    # 'useless' placeholders to prevent crash if missing in game log
    PD_SELECTOR = PD_CHOICE = ON_PLAY = ON_DRAW = ""
    P1_MULLS = P2_MULLS = TURNS = 0

    try:
        P1, P2 = players(match_actions)[0:2]
    except ValueError:
        return "Players not Found."
    curr_game_list = []
    initial_player_count = join_countdown = len(players(match_actions))
    MATCH_ID = match_actions[0]

    for action in match_actions:
        current_action_list = action.split()
        # all players joining indicate a break between games
        if "joined the game" in action:
            if join_countdown > 0:
                join_countdown -= 1
            else:
                # New Game, reset countdown
                join_countdown = initial_player_count
                join_countdown -= 1
                GAME_WINNER = get_winner(curr_game_list, P1, P2)
                if GAME_WINNER == "NA":
                    ALL_GAMES_GA[f"{MATCH_ID}-{GAME_NUM}"] = curr_game_list
                ALL_PARSED_GAMES.append([
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
                    GAME_WINNER])
                curr_game_list = []
        elif "chooses to" in action and "play first" in action:
            GAME_NUM += 1
            PD_SELECTOR = "P1" if current_action_list[0] == P1 else 'P2'
            PD_CHOICE = "Play" if current_action_list[3] == "play" else 'Draw'
            if PD_CHOICE == "Play":
                ON_PLAY = PD_SELECTOR
                ON_DRAW = "P2" if PD_SELECTOR == 'P1' else 'P1'
            else:
                ON_PLAY = "P2" if PD_SELECTOR == 'P1' else 'P1'
                ON_DRAW = PD_SELECTOR
        elif "begins the game with" in action and "cards in hand" in action:
            if P1 == current_action_list[0]:
                P1_MULLS = MULL_DICT[action.split(" begins the game with ")[1].split()[0]]
            elif P2 == current_action_list[0]:
                P2_MULLS = MULL_DICT[action.split(" begins the game with ")[1].split()[0]]
        elif "Turn " in action and len(current_action_list) == 3:
            TURNS = int(current_action_list[1].split(":")[0])
        curr_game_list.append(action)
    GAME_WINNER = get_winner(curr_game_list,P1,P2)
    if GAME_WINNER == "NA":
        ALL_GAMES_GA[f"{MATCH_ID}-{GAME_NUM}"] = curr_game_list
    ALL_PARSED_GAMES.append([
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
        GAME_WINNER])
    return (ALL_PARSED_GAMES, ALL_GAMES_GA)

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

def play_data(game_actions: list[str]):
    # Input:  List[GameActions]
    # Output: List[Plays]

    PLAY_DATA = []
    ALL_PLAYS = []

    GAME_NUM = 0
    PLAY_NUM = 0
    TURN_NUM = 0
    ACTIVE_PLAYER = ""
    NON_ACTIVE_PLAYER = ""

    P1, P2 = players(game_actions)[0:2]
    turn_regex = new_turn_regex([P1,P2])
    MATCH_ID = game_actions[0]

    for i in game_actions:
        curr_word_list = i.split()
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
        new_turn_match = turn_regex.search(i)
        if "chooses to " in i and ' play first' in i:
            GAME_NUM += 1
            PLAY_NUM = 0
        elif new_turn_match:
            TURN_NUM = int(new_turn_match[1])
            ACTIVE_PLAYER = new_turn_match[2]
            NON_ACTIVE_PLAYER = P2 if ACTIVE_PLAYER == P1 else P1

        elif is_play(i):
            if curr_word_list[1] == "plays":
                CASTING_PLAYER = curr_word_list[0]
                try:
                    PRIMARY_CARD = get_cards(i)[0]
                # MODO Bug Encountered. Primary_Card = "NA"
                except IndexError:
                    pass
                ACTION = "Land Drop"
            elif curr_word_list[1] == "casts":
                CASTING_PLAYER = curr_word_list[0]
                try:
                    PRIMARY_CARD = get_cards(i)[0]
                # MODO Bug Encountered. Primary_Card = "NA"
                except IndexError:
                    pass
                ACTION = curr_word_list[1].capitalize()
                if "targeting" in i:
                    target_string = i.split("targeting")[1]
                    targets = get_cards(target_string)
                    try:
                        TARGET_1 = targets[0]
                        TARGET_2 = targets[1]
                        TARGET_3 = targets[2]
                    except IndexError:
                        pass
                    SELF_TARGET = player_is_target(target_string, CASTING_PLAYER)
                    OPP_TARGET = player_is_target(
                        target_string, P1 if CASTING_PLAYER == P2 else P2)
            elif curr_word_list[1] == "draws":
                CASTING_PLAYER = curr_word_list[0]
                ACTION = 'Draws'
                CARDS_DRAWN = CARDS_DRAWN_DICT.get(curr_word_list[2], 8)
            elif curr_word_list[1] == "chooses":
                continue
            elif i.find("activates an ability of") != -1:
                CASTING_PLAYER = curr_word_list[0]
                try:
                    PRIMARY_CARD = get_cards(i)[0]
                except IndexError:
                    PRIMARY_CARD = i.split("activates an ability of ")[1].split(" (")[0]
                    # MODO Bug Encountered. Primary_Card = "NA"
                    if (PRIMARY_CARD == P1) or (PRIMARY_CARD == P2):
                        PRIMARY_CARD = "NA"
                ACTION = "Activated Ability"
                if "targeting" in i:
                    target_string = i.split("targeting")[1]
                    targets = get_cards(target_string)
                    try:
                        TARGET_1 = targets[0]
                        TARGET_2 = targets[1]
                        TARGET_3 = targets[2]
                    except IndexError:
                        pass
                    SELF_TARGET = player_is_target(target_string,CASTING_PLAYER)
                    OPP_TARGET = player_is_target(
                        target_string, P1 if CASTING_PLAYER == P2 else P2)
            elif curr_word_list[1] == "discards":
                CASTING_PLAYER = curr_word_list[0]
                ACTION = 'Discards'
                try:
                    PRIMARY_CARD = get_cards(i)[0]
                except:
                    PRIMARY_CARD = 'NA'
            elif "is being attacked by" in i:
                CASTING_PLAYER = ACTIVE_PLAYER
                ACTION = "Attacks"
                ATTACKERS = len(get_cards(i.split("is being attacked by")[1]))
            elif i.find("puts triggered ability from") != -1:
                CASTING_PLAYER = curr_word_list[0]
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
    
    match_actions = all_actions(game_log)
    # old match id was just the last modified time. Now using ingame ID
    # gameactions.insert(0, strftime(r'%Y%m%d%H%M', file_last_modified))
    gamedata = game_data(match_actions)
    if isinstance(gamedata, str):
        return gamedata
    playdata = play_data(match_actions)
    matchdata = match_data(match_actions,gamedata[0],playdata)
    matchdata[-1] = strftime(r'%Y-%m-%d-%H:%M', file_last_modified)
    if isinstance(matchdata, str):
        return matchdata
    timeout = check_timeout(match_actions)

    return [matchdata,gamedata[0],playdata,gamedata[1],timeout]
