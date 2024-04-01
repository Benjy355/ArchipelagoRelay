#Functions used to get information from the archipelago.gg multiworld pages.

import requests
from bs4 import BeautifulSoup


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
    def from_soup(cls, soup: BeautifulSoup = None):
        columns = soup.find_all("td")
        id = columns[0].text
        name = columns[1].find("a").text
        game = columns[2].text
        download_link = columns[3].find("a").attrs['href']
        tracker_page = columns[4].find("a").attrs['href']
        return cls(id=id, name=name, game=game, download_link=download_link, tracker_page=tracker_page)
        

class archipelago_site_data:
    #Container for multiworld.gg site information; glorified dict
    game_id: str = None
    players: list[archipelago_site_slot_data] = []

    def __init__(self):
        self.game_id = None
        self.players = []

async def get_site_data(url: str) -> archipelago_site_data:
    #Takes a url to https://archipelago.gg/room/... and returns out a site_data object
    return_data = archipelago_site_data()
    page_request = requests.get(url=url)

    main_bs = BeautifulSoup(page_request.content, "html.parser")
    return_data.game_id = main_bs.find("title").text[11:] # Cut out "multiworld " from the title

    all_tables = main_bs.find_all("table")
    # There should only be one table.
    if (len(all_tables) > 0):
        try:
            main_table: BeautifulSoup = all_tables[0]
            players_html = main_table.find("tbody").find_all("tr")

            for player_html in players_html:
                return_data.players.append(archipelago_site_slot_data.from_soup(player_html))
        
            return return_data
        except: #TODO: LOG THE EXCEPTION DETAILS
            return None
    else:
        return None