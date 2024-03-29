import logging
import time
import argparse
import requests
import configparser
from howlongtobeatpy import HowLongToBeat
from statistics import mean

logger = logging.getLogger()
temps_debut = time.time()

PROTONDB_RATINGS = {
    "Platinum": 4,
    "Gold": 3,
    "Silver": 2,
    "Bronze": 1,
    "Borked": 0,
}


def read_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config


def get_appid_from_steam_url(url):
    # TODO might cause error if urls are incorrect, appid should be an int
    try:
        return int(url.split("/")[4])
    except Exception as e:
        logger.error(f"{url} is not a correct Steam URL : {e}.")
        return None


def get_steam_info(appid):
    url_info_game = f"http://store.steampowered.com/api/appdetails?appids={appid}"
    info_dict = requests.get(url_info_game).json()
    info_dict_data = info_dict[str(appid)]["data"]

    url_reviews = (
        f"https://store.steampowered.com/appreviews/{appid}?json=1&language=all"
    )
    reviews_dict = requests.get(url_reviews).json()
    reviews_dict_data = reviews_dict["query_summary"]
    if info_dict_data and reviews_dict_data:
        return {
            "appid": appid,
            "name": info_dict_data["name"] if "name" in info_dict_data else None,
            "platforms": ", ".join(
                [k.title() for k, v in info_dict_data["platforms"].items() if v]
            )
            if "platforms" in info_dict_data
            else None,
            "release_date": info_dict_data["release_date"]
            if "release_date" in info_dict_data
            else None,
            "review_score_desc": reviews_dict_data["review_score_desc"]
            if "review_score_desc" in reviews_dict_data
            else None,
            "total_positive": reviews_dict_data["total_positive"]
            if "total_positive" in reviews_dict_data
            else None,
            "total_reviews": reviews_dict_data["total_reviews"]
            if "total_reviews" in reviews_dict_data
            else None,
        }
    else:
        logger.error(f"Couldn't retrieve Steam infos for game {appid}.")
        return None


def get_itad_plain(api_key, appid):
    url = f"https://api.isthereanydeal.com/v02/game/plain/?key={api_key}&shop=steam&game_id=app%2F{appid}&url=&title=&optional="
    result = requests.get(url).json()
    logger.debug(f"{url}: {result}")
    if result:
        if isinstance(result["data"], dict):
            if "plain" in result["data"]:
                return result["data"]["plain"]
    return None


def get_itad_historical_low(api_key, plain, region, country):
    url = f"https://api.isthereanydeal.com/v01/game/lowest/?key={api_key}&plains={plain}&region={region}&country={country}"
    result = requests.get(url).json()
    logger.debug(f"{url}: {result}")
    if result:
        if "price" in result["data"][plain]:
            return {
                "historical_low_price": result["data"][plain]["price"],
                "historical_low_currency": result[".meta"]["currency"],
                "historical_low_shop": result["data"][plain]["shop"]["name"],
            }
    return None


def get_itad_current_price(api_key, appid, plain, region, country):
    url = f"https://api.isthereanydeal.com/v01/game/prices/?key={api_key}&plains={plain}&region={region}&country={country}&shops=steam&added=0"
    result = requests.get(url).json()
    # for some reasons there are sometimes several entries for one game. Get the one with the correct Steam URL.
    correct_result = None
    for x in result["data"][plain]["list"]:
        if str(appid) in x["url"]:
            correct_result = x
    logger.debug(f"{url}: {correct_result}")
    if correct_result:
        return {
            "current_price_price": correct_result["price_new"],
            "current_price_currency": result[".meta"]["currency"],
            "current_price_shop": correct_result["shop"]["name"],
        }
    else:
        return None


def get_itad_infos(api_key, appid):
    # plain is the internal itad id for a game
    plain = get_itad_plain(api_key, appid)
    if plain:
        historical_low = get_itad_historical_low(api_key, plain, "us", "US")
        current_price = get_itad_current_price(api_key, appid, plain, "us", "US")
    else:
        historical_low = None
        current_price = None
    if plain and historical_low and current_price:
        return {
            "appid": appid,
            "plain": plain,
            "historical_low_price": historical_low["historical_low_price"]
            if "historical_low_price" in historical_low
            else None,
            "historical_low_currency": historical_low["historical_low_currency"]
            if "historical_low_currency" in historical_low
            else None,
            "historical_low_shop": historical_low["historical_low_shop"]
            if "historical_low_shop" in historical_low
            else None,
            "current_price_price": current_price["current_price_price"]
            if "current_price_price" in current_price
            else None,
            "current_price_currency": current_price["current_price_currency"]
            if "current_price_currency" in current_price
            else None,
            "current_price_shop": current_price["current_price_shop"]
            if "current_price_shop" in current_price
            else None,
        }
    else:
        return None


# def get_opencritic_id(search):
#     url = f"https://api.opencritic.com/api/game/search?criteria={search}"
#     result = requests.get(url).json()
#     logger.debug(f"opencritic result: {result}")

#     if result:
#         if "API key is required" in result["message"]:
#             return None
#         return result[0]["id"]
#     else:
#         return None


# def get_opencritic_infos(search):
#     opencritic_id = get_opencritic_id(search)
#     if opencritic_id:
#         url = f"https://api.opencritic.com/api/game/{opencritic_id}"
#         result = requests.get(url).json()

#         return {
#             "opencritic_tier": result["tier"],
#             "opencritic_median_score": result["medianScore"],
#             "opencritic_reviews_number": result["numReviews"],
#         }
#     return None


def get_howlongtobeat_infos(search):
    result = HowLongToBeat().search(search)
    if result:
        return {
            "howlongtobeat_url": result[0].game_web_link,
            "howlongtobeat_main": result[0].main_story,
            "howlongtobeat_main_extra": result[0].main_extra,
            "howlongtobeat_completionist": result[0].completionist,
        }
    return None


def get_protondb_infos(appid):
    # TODO
    url = f"https://protondb.max-p.me/games/{appid}/reports"
    protondb_url = f"https://www.protondb.com/app/{appid}"
    result = requests.get(url).json()
    mean_score = 0
    if len(result) > 0:
        tiers = [x["rating"] for x in result]
        mean_score = int(round(mean([PROTONDB_RATINGS[x] for x in tiers]), 0))
    rating = list(PROTONDB_RATINGS.keys())[
        list(PROTONDB_RATINGS.values()).index(mean_score)
    ]
    return {"protondb_url": protondb_url, "protondb_rating": rating}


def get_game_infos(urls):
    config = read_config()
    itad_api = config["ITAD"]["api_key"]

    list_game_infos = []
    for url in urls:
        logger.info(f"Processing {url}.")
        appid = get_appid_from_steam_url(url)
        if appid:
            # Steam
            steam_infos = get_steam_info(appid)
            logger.debug(f"Steam: {steam_infos}")
            if steam_infos:
                # ITAD
                itad_infos = get_itad_infos(itad_api, appid)
                logger.debug(f"ITAD: {itad_infos}")
                # Opencritic
                # opencritic_infos = get_opencritic_infos(steam_infos["name"])
                # logger.debug(f"Opencritic: {opencritic_infos}")
                # HowLongToBeat
                howlongtobeat_infos = get_howlongtobeat_infos(steam_infos["name"])
                logger.debug(f"HowLongToBeat: {howlongtobeat_infos}")
                # ProtonDB
                # protondb_infos = get_protondb_infos(appid)
                # logger.debug(f"ProtonDB: {protondb_infos}")
                list_game_infos.append(
                    {
                        "appid": appid,
                        "url": url,
                        "steam": steam_infos,
                        "itad": itad_infos,
                        # "opencritic": opencritic_infos,
                        "howlongtobeat": howlongtobeat_infos,
                        # "protondb": protondb_infos,
                    }
                )

    return list_game_infos


def parse_release_date(release_date):
    """Transform '4 Feb, 2021' to '2021-02-04'"""
    months = {
        "Jan": "01",
        "Feb": "02",
        "Mar": "03",
        "Apr": "04",
        "MAY": "05",
        "May": "05",
        "Jun": "06",
        "Jul": "07",
        "Aug": "08",
        "Sep": "09",
        "Oct": "10",
        "Nov": "11",
        "Dec": "12",
        # Sometimes the steam API returns date in other languages
        "июн": "06",
        "июл": "07",
        "października": "10",
        "sierpnia": "08",
        "авг": "08",
        "мая": "03",
        "ноя": "11",
        "окт": "10",
        "сен": "09",
        "фев": "02",
        "янв": "01",
        "年": "01",
    }

    logger.debug(f"Parsing date {release_date}...")
    tokens = release_date.replace(".", "").replace(",", "").split(" ")
    return "-".join([tokens[2], months[tokens[1]], tokens[0].zfill(2)])


def format_game_info(game_info):
    percentage_reviews = round(
        game_info["steam"]["total_positive"]
        / game_info["steam"]["total_reviews"]
        * 100,
        2,
    )
    release_date = (
        f"{parse_release_date(game_info['steam']['release_date']['date'])}"
        if "date" in game_info["steam"]["release_date"]
        else ""
    )
    platforms = game_info["steam"]["platforms"]
    name = game_info["steam"]["name"]
    url = game_info["url"]
    review_score_desc = game_info["steam"]["review_score_desc"]
    total_reviews = game_info["steam"]["total_reviews"]

    if game_info["itad"]:
        current_price = (
            (
                f"{round(game_info['itad']['current_price_price'], 2)}"
                f" {game_info['itad']['current_price_currency']}"
            )
            if game_info["itad"]["current_price_price"]
            and game_info["itad"]["current_price_currency"]
            and game_info["itad"]["current_price_shop"]
            else " "
        )
        historical_low = (
            (
                f"{round(game_info['itad']['historical_low_price'], 2)}"
                f" {game_info['itad']['historical_low_currency']}"
                f" @{game_info['itad']['historical_low_shop']}"
            )
            if game_info["itad"]["historical_low_price"]
            and game_info["itad"]["historical_low_currency"]
            and game_info["itad"]["historical_low_shop"]
            else " "
        )
    else:
        current_price = ""
        historical_low = ""

    if game_info["howlongtobeat"]:
        howlongtobeat_main = (
            game_info["howlongtobeat"]["howlongtobeat_main"]
            if "howlongtobeat" in game_info
            and "howlongtobeat_main" in game_info["howlongtobeat"]
            and game_info["howlongtobeat"]["howlongtobeat_main"] not in [-1]
            else ""
        )
        howlongtobeat_url = (
            game_info["howlongtobeat"]["howlongtobeat_url"]
            if "howlongtobeat" in game_info
            and "howlongtobeat_url" in game_info["howlongtobeat"]
            and game_info["howlongtobeat"]["howlongtobeat_url"]
            else ""
        )
        howlongtobeat_format = (
            f"[{howlongtobeat_main} Hours]({howlongtobeat_url})"
            if howlongtobeat_main != ""
            and howlongtobeat_url != ""
            else ""
        )
    else:
        howlongtobeat_main = ""
        howlongtobeat_url = ""
        howlongtobeat_format = ""

    # opencritic_median_score = ""
    # if game_info["opencritic"]:
    #     if game_info["opencritic"]["opencritic_median_score"] > -1:
    #         opencritic_median_score = game_info["opencritic"]["opencritic_median_score"]

    return (
        f"|[{name}]({url})"
        f"|{total_reviews}"
        f"|{percentage_reviews}% ({review_score_desc})"
        f"|{release_date}"
        f"|{current_price}"
        f"|{historical_low}"
        f"|{platforms}"
        # Opencritic
        # f"|{opencritic_median_score}"
        # HowLongToBeat
        f"|{howlongtobeat_format}"
        # ProtonDB
        # f"|[{game_info['protondb']['protondb_rating']}]({game_info['protondb']['protondb_url']})"
        # f"||"
        f"|"
    )


def get_game_info_for_url(url, game_infos):
    for i in game_infos:
        if i["url"] == url:
            return i
    return None


def create_output(game_infos, file_content):
    content = []
    header = (
        "|Game"
        "|Steam Reviews: Number"
        "|Steam Reviews: Score"
        "|Release Date"
        "|Steam Price"
        "|Historic Lowest Price"
        "|Platforms"
        "|[How Long To Beat?](https://howlongtobeat.com/) Main Story"
        "|"
    )
    # "|[Opencritic](https://opencritic.com/) (TCA/100)"
    # separator = "|:-|:-|:-|:-|:-|:-|:-|:-|:-|"
    separator = "|:-|:-|:-|:-|:-|:-|:-|:-|"
    if not any([len(x) > 1 for x in file_content]):
        content = [format_game_info(x) for x in game_infos]
        content.insert(0, separator)
        content.insert(0, header)
    # new format with tiers
    else:
        for line in file_content:
            if len(line) > 2:
                raise ValueError(
                    "File content malformed. See example file for help about the format."
                )
            if len(line) == 2:
                content.append(f"**{line[0].replace('_', ' ')} - {line[1]}**\n")
                content.append(header)
                content.append(separator)
            else:
                game_info = get_game_info_for_url(line[0], game_infos)
                if game_info:
                    content.append(format_game_info(game_info))
                else:
                    logger.warning(
                        f"Wasn't able to retrieve data for {line} in game_info."
                    )
    return "\n".join(content)


def main():
    args = parse_args()
    with open(args.file, "r") as f:
        file_content = [x.strip().split(" ") for x in f.readlines()]

    game_infos = get_game_infos([x[0] for x in file_content if len(x) == 1])
    output = create_output(game_infos, file_content)

    output_filename = f"{int(time.time())}_game_deals.txt"
    with open(output_filename, "w") as f:
        f.write(output)

    logger.info("Runtime : %.2f seconds." % (time.time() - temps_debut))


def parse_args():
    format = "%(levelname)s :: %(message)s"
    parser = argparse.ArgumentParser(description="Game Overview Table")
    parser.add_argument(
        "--debug",
        help="Display debugging information.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    parser.add_argument("file", nargs="?", type=str, help="File containing Steam urls.")
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel, format=format)
    return args


if __name__ == "__main__":
    main()
