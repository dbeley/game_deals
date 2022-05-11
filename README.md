# game_deals

This script will create a formatted reddit markdown table from a list of steam games.

## Requirements

- python
- requests

## Installation

- Install the requirements (python + requests library)
- Clone the repo
- Check how to use the script with:

```
python game_deals.py -h
```

## Configuration

- Create an API key on https://isthereanydeal.com/dev/app/
- Copy the `config_example.ini` file to another file named `config.ini`
- Replace `ITAD_API_KEY_HERE` with your own API key in `config.ini`

## Usage

- Create a text file containing several steam game URLs (one per line).

```
https://store.steampowered.com/app/466560/Northgard/
https://store.steampowered.com/app/1080110/F1_2020/
https://store.steampowered.com/app/588650/Dead_Cells/
https://store.steampowered.com/app/255710/Cities_Skylines/
```

Example files are also provided see `example.txt` and `example-with-tiers.txt`.

- Run the script: `python game_deals.py FILENAME.txt`

This will create a file named `TIMESTAMP_game_deals.txt`.

## Credits

- [Steam](https://store.steampowered.com/)
- [IsThereAnyDeal](https://isthereanydeal.com/)
- [Opencritic](https://opencritic.com/)
- [HowLongToBeat](https://howlongtobeat.com/)
