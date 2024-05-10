#Functions used to get information from the archipelago.gg multiworld pages.

import requests
from bs4 import BeautifulSoup
import logging
logger = logging.getLogger(__name__)

import os, sys

class archipelago_site_slot_data:
    #Container for archipelago_site_data players dict
    id = None
    name = None
    game = None
    download_link = None
    tracker_page = None

    def __init__(self, id = None, name = None, game = None, download_link = None, tracker_page = None):
        self.id = id
        self.name = name
        self.game = game
        self.download_link = download_link # RELATIVE LINK "/slot_file/..."
        self.tracker_page = tracker_page # RELATIVE LINK "/tracker/...."

    @classmethod
    def from_soup(cls, soup: BeautifulSoup):
        columns = soup.find_all("td")
        id = columns[0].text
        name = columns[1].find("a").text
        game = columns[2].text

        dl_a = columns[3].find("a")
        if (dl_a != None):
            download_link = dl_a.attrs['href']
        else:
            download_link = None
        
        tp_a = columns[4].find("a")
        if (tp_a != None):
            tracker_page = tp_a.attrs['href']
        else:
            tracker_page = None

        return cls(id=id, name=name, game=game, download_link=download_link, tracker_page=tracker_page)
        

class archipelago_site_data:
    #Container for multiworld.gg site information; glorified dict
    game_id: str = None
    port: str = None
    players: list[archipelago_site_slot_data] = []

    def __init__(self):
        self.game_id = None
        self.port = None
        self.players = []

def get_site_data(url: str) -> archipelago_site_data:
    #Takes a url to https://archipelago.gg/room/... and returns out a site_data object
    return_data = archipelago_site_data()
    page_request = requests.get(url=url)

    main_bs = BeautifulSoup(page_request.content, "html.parser")

    #Get the game ID from the <title> field
    return_data.game_id = main_bs.find("title").text[11:] # Cut out "multiworld " from the title
    
    #Get the port, luckily (so far) there is only one span! Huzzah!
    # We will grab the "data-tooltip" arg and take the final 6 characters, then cut off the last one (port is *58967*.)
    return_data.port = main_bs.find("span").attrs['data-tooltip'][-6:-1]

    all_tables = main_bs.find_all("table")
    # There should only be one table, where we have all the player info we want
    if (len(all_tables) > 0):
        try:
            main_table: BeautifulSoup = all_tables[0]
            players_html = main_table.find("tbody").find_all("tr")

            for player_html in players_html:
                return_data.players.append(archipelago_site_slot_data.from_soup(player_html))
        
            return return_data
        except Exception as e: #TODO: LOG THE EXCEPTION DETAILS
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logging.error("[RECEIVE_DATA_LOOP]")
            logging.error([exc_type, fname, exc_tb.tb_lineno])
            logging.error(e)
            return None
    else:
        return None