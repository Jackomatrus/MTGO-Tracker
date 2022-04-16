
def parse_draft_log(file,initial):
    PICKS_TABLE = []
    DRAFTS_TABLE = []

    DRAFT_ID = ""
    DATE = ""
    EVENT_NUM = ""
    HERO = ""
    PLAYER_LIST = []
    FORMAT = ""
    CARD = ""
    AVAIL_LIST = []
    PACK_NUM = 0
    PICK_NUM = 0
    PICK_OVR = 0
    FORMAT = file.split("-")[-1].split(".")[0]

    player_bool = False
    card_bool = False
    last_pack_size = 0
    init = initial.split("\n")

    for i in init:
        if "Event #: " in i:
            EVENT_NUM = i.split()[-1]
        elif "Time:    " in i:
            year = i.split("/")[2].split()[0]
            month = i.split("/")[0].split()[-1]
            day = i.split("/")[1]
            hour = i.split()[2].split(":")[0]
            minute = i.split()[2].split(":")[1]
            if (i.split()[-1] == "AM") & (hour == "12"):
                hour = "00"
            if (i.split()[-1] == "PM") & (hour != "12"):
                hour = str(int(hour) + 12)
            if len(month) == 1:
                month = "0" + month
            if len(day) == 1:
                day = "0" + day
            if len(hour) == 1:
                hour = "0" + hour
            DATE = f"{year}-{month}-{day}-{hour}:{minute}"
        elif i == "Players:":
            player_bool = True
        elif i == "":
            if player_bool:
                player_bool = False
            if card_bool:
                card_bool = False
                if len(AVAIL_LIST) > last_pack_size:
                    PACK_NUM += 1
                    PICK_NUM = 1
                last_pack_size = len(AVAIL_LIST)
                while len(AVAIL_LIST) < 14:
                    AVAIL_LIST.append("NA")
                PICKS_TABLE.append([DRAFT_ID,CARD,PACK_NUM,PICK_NUM,PICK_OVR] + AVAIL_LIST)
                AVAIL_LIST = []
        elif ('Pack' in i) & (" pick " in i) & (len(i.split()) == 4):
            card_bool = True
        elif player_bool:
            if "--> " in i:
                HERO = i[4:]
                DRAFT_ID = f"{year}{month}{day}{hour}{minute}_{HERO}_{FORMAT}_{EVENT_NUM}"
            else:
                PLAYER_LIST.append(i[4:])
        elif card_bool:
            if "--> " in i:
                CARD = i.split("--> ")[1]
                PICK_NUM += 1
                PICK_OVR += 1
            else:
                AVAIL_LIST.append(i.split("    ")[1])
    while len(PLAYER_LIST) < 7:
        PLAYER_LIST.append("NA")
    DRAFTS_TABLE.append([DRAFT_ID,HERO] + PLAYER_LIST + [0,0,FORMAT,DATE])

    return (DRAFTS_TABLE,PICKS_TABLE,DRAFT_ID)
