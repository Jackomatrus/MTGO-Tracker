from typing import Literal
from MODO_DATA import (GAME_HEADER, LIMITED_FORMATS, PLAYS_HEADER, 
    MATCHES_HEADER, CARD_PATTERN)
import re

class MatchActions(list):
    def __init__(self, *args):
        super(MatchActions, self).__init__(*args)
    
    @property
    def match_id(self) -> str:
        if len(self):
            return self[0]
        else:
            return "NA"
    @match_id.setter
    def match_id(self, new):
        match_id_re = re.compile(r'[0-9a-zA-Z-]{36}_.+?_.+')
        if not match_id_re.fullmatch(new):
            raise ValueError(
                f'Match_ID needs to be 36 characters followed by '
                f'_P1name_P2name, got\n{new}')
        self[0] = new
    
    @property
    def players(self):
        player_name_re = re.compile(r'^(.*?) joined the game', re.MULTILINE)
        players_list = list(set(player_name_re.findall('\n'.join(self))))
        players_list.sort(key=len, reverse=True)
        return players_list

def property_factory(index):
    def getter(self):
        return self[index]
    def setter(self, value):
        self[index] = value
    return property(getter, setter)

class GameData(list):
    Match_ID: str
    P1: str
    P2: str
    Game_Num: Literal[1,2,3]
    PD_Selector: Literal['P1','P2']
    PD_Choice: Literal['Play','Draw']
    On_Play: Literal['P1','P2']
    On_Draw:  Literal['P1','P2']
    P1_Mulls: int
    P2_Mulls: int
    Turns: int
    Game_Winner: Literal['P1','P2']

    def __init__(self, *args):
        super(GameData, self).__init__(*args)
        # fill up so all properties can be accessed
        self.extend([''] * (12 - len(self)))

    for category in GAME_HEADER:
        exec(f'{category} = property_factory(GAME_HEADER.index("{category}"))')

class MatchData(list):
    Match_ID: str
    Draft_ID: str
    P1: str
    P1_Arch: str
    P1_Subarch: str
    P2: str
    P2_Arch: str
    P2_Subarch: str
    P1_Roll: int
    P2_Roll: int
    Roll_Winner: Literal['P1','P2']
    P1_Wins: Literal[0,1,2]
    P2_Wins: Literal[0,1,2]
    Match_Winner: Literal['P1','P2']
    Format: str
    Limited_Format: str
    Match_Type: str
    Date: str

    def __init__(self, *args):
        super(MatchData, self).__init__(*args)
        # fill up so all properties can be accessed
        self.extend([''] * (18 - len(self)))
    
    for category in MATCHES_HEADER:
        exec(f'{category} = property_factory(MATCHES_HEADER.index("{category}"))')

class PlayData(list):
    Match_ID: str
    Game_Num: Literal[1,2,3]
    Play_Num: int
    Turn_Num: int
    Casting_Player: str
    Action: Literal['Discards', 'Triggers', "Activated Ability", 
                    'Draws', 'Casts', "Land Drop", 'Attacks']
    Primary_Card: str
    Target1: str
    Target2: str
    Target3: str
    Opp_Target: Literal[0,1]
    Self_Target: Literal[0,1]
    Cards_Drawn: int
    Attackers: int
    Active_Player: str
    Nonactive_Player: str

    def __init__(self, *args):
        super(PlayData, self).__init__(*args)
        # fill up so all properties can be accessed
        self.extend([''] * (16 - len(self)))
    
    def parse_targets(self, action_string: str) -> None:
        """Sets the target of this play by parsing the whole log line.

        Args:
            action_string (str): The line in the game log that describes this play.
        """
        self.Target1 = self.Target2 = self.Target3 = 'NA'
        self.Opp_Target = self.Self_Target = 0
        if 'targeting' not in action_string:
            return
        target_string = action_string.split("targeting")[1]
        targets = CARD_PATTERN.findall(target_string)
        try:
            self.Target1 = targets[0]
            self.Target2 = targets[1]
            self.Target3 = targets[2]
        except IndexError:
            pass
        without_brackets = re.sub(r'\[.*?\]', '', target_string)
        self.Self_Target = int(self.Casting_Player in without_brackets)
        other_player = (
            self.Nonactive_Player if self.Casting_Player == self.Active_Player 
            else self.Active_Player)
        self.Opp_Target = int(other_player in without_brackets)
    for category in PLAYS_HEADER:
        exec(f'{category} = property_factory(PLAYS_HEADER.index("{category}"))')

class AllData(list):
    def __init__(self, *args):
        if len(args) == 0:
            super(AllData, self).__init__([[],[],[],{}])
        else:
            super(AllData, self).__init__(*args)
    matches = property_factory(0)
    games = property_factory(1)
    plays = property_factory(2)
    raw_game_data_dict = property_factory(3)