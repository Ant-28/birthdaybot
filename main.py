import discord
from discord.ext import commands, tasks
from discord import app_commands  # type: ignore
from dotenv import dotenv_values
from typing import Dict, List, Any, Set
import datetime
from datetime import date # type: ignore

from db import BirthdayDB
from zoneinfo import ZoneInfo, available_timezones
config : Dict[str, str | None] = dotenv_values(".env")


APIKEY = config["TOKEN"]
SERVERID = config["SERVERID"]
print(SERVERID)
GUILD_ID = discord.Object(id=SERVERID) if SERVERID else None
GUILD_ID_INT = int(SERVERID) if SERVERID else None
intents = discord.Intents.default()
intents.message_content = True
TIMEZONES = available_timezones()
print(TIMEZONES)
# get all IANA time zones on my device
async def IANA_autocomplete(interaction: discord.Interaction, 
                            current: str) -> List[app_commands.Choice[str]]:
    return [app_commands.Choice(name=tz, value=tz) for tz in TIMEZONES if current.lower() in tz.lower()][:10]


class MyClient(commands.Bot):
    async def on_ready(self):
        # this should 1. poll the current time and try running a cron job
        try:    
            self.db = BirthdayDB()
            synced = await self.tree.sync(guild=GUILD_ID)
            if GUILD_ID: 
                print(f"Synced {len(synced)} commands to {GUILD_ID.id}")
            
            self.data_snapshot : Dict[str, Dict[str, str]] = await self.get_alldata() # get all current birthdays from the database
            self.midnights: List[datetime.time] = self.get_midnights()
            self.birthdaycheck.start()
            if self.birthdaycheck.is_running():
                self.birthdaycheck.change_interval(time = self.midnights)
                # print("birthdaycheck is running")
                # self.birthdaycheck.change_interval(time = [datetime.time(hour = 1, minute = 37, tzinfo = ZoneInfo("Asia/Calcutta"))])
                self.birthdaycheck.restart()
            else:
                print('what')
        except Exception as e:
            print(f"Error synching commands {e}")
        
        print(f"Logged on as {self.user}")
    # on message really need not do anything
    
    # get midnight at every time zone stored in the database
    def get_midnights(self) -> List[datetime.time]:
        times : List[datetime.time] = []
        timzeones : Set[str] = set()
        for _, v in self.data_snapshot.items():
            timzeones.add(v["tz"])
        for time in timzeones:
            times.append(datetime.time(hour = 0, minute = 0, tzinfo = ZoneInfo(time)))
        if not times:
            return [datetime.time(hour = 0, minute = 0, tzinfo = ZoneInfo("America/Los_Angeles"))]
        return times

    async def get_channelnames(self,interaction: discord.Interaction, 
                            current: str) -> List[app_commands.Choice[str]]:
        try: 
            g = self.get_guild(GUILD_ID_INT) # type: ignore
            if g:
                return [app_commands.Choice(name = gx.name, value= gx.name) \
                        for gx in g.text_channels \
                        if current in gx.name][:10]
            await interaction.response.send_message("Couldn't find channel names!")
            return []
        except Exception as e:
            raise Exception(e) 
    
    async def get_alldata(self) -> Dict[str, Any]:
        keys : List[int] = await self.db.getKeys() 
        data = {}
        for key in keys:
            data[key] = await self.db.getBirthday(key)
        return data  # pyright: ignore[reportUnknownVariableType]

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return
        # if not message:
        #     print(f"Message was probably empty")
        #     return
        # await message.channel.send(f"Message from {message.author} : {message.content}!")
    @tasks.loop(time=[datetime.time(hour = 0, minute = 0, tzinfo = ZoneInfo("Asia/Calcutta"))])
    async def birthdaycheck(self):
        await self.wait_until_ready()
        remind_channel_id = await self.db.getChannelID()
        if not remind_channel_id:
            raise Exception("Client has not set a channel id to wish birthdays in")
        remind_channel = self.get_channel(remind_channel_id)
        if remind_channel is not None: 
            await remind_channel.send("It sure is a midnight") # type: ignore
        for userid, data in self.data_snapshot.items():
            try:
                birthdayinfo = data["date"]
                tz           = data["tz"]
                print(birthdayinfo)
                birthday = datetime.datetime.fromisoformat(birthdayinfo).date()
                print(birthday)
                print(datetime.datetime.now().astimezone(ZoneInfo(tz)).date())
                if datetime.datetime.now().astimezone(ZoneInfo(tz)).date() == birthday:
                    await remind_channel.send(f"Happy Birthday, <@{userid}>!") # type: ignore
            except Exception as e:
                print(f"Some error occured when sending a birthday, {e}")


# the command prefix isn't used???
client = MyClient(command_prefix="!", intents=intents)


# ok so
# client commands can be global or per-server
# when testing, set this to per-server

@client.tree.command(name="setbirthday", description="Sets your birthday", guild=GUILD_ID)
@app_commands.describe(
    year="Your year of birth",
    month="Your month of birth",
    day="Your day of birth",
    tz="Your timezone, in IANA format"
)
@app_commands.autocomplete(tz=IANA_autocomplete)
async def setbirthday(interaction: discord.Interaction, year: int, month: int, day: int, tz: str): 
    try:
        mybirthday = date(year, month, day)
        if tz not in TIMEZONES: 
            await interaction.response.send_message("Please select an IANA timezone from the drop-down menu")
            return
        if not (await client.db.getChannelID()):
            await interaction.response.send_message("Please set a channel to wish people in first!")
            return
        await client.db.writeBirthday(interaction.user.id, f"{mybirthday}", tz)
        # now update birthdays
        client.data_snapshot = await client.get_alldata() # get all current birthdays from the database
        client.midnights = client.get_midnights()

        if not client.birthdaycheck.is_running():
            client.birthdaycheck.start()
        
        client.birthdaycheck.change_interval(time = client.midnights)
        client.birthdaycheck.restart()
        print(f"restarted birthdaycheck {client.birthdaycheck.is_running()} {client.birthdaycheck.time}")
        await interaction.response.send_message(f"Your birthday is... {mybirthday} {tz}.\nThis has been set in the database.")
        
        
    
    except ValueError:
        await interaction.response.send_message(f"That didn't work! Could you try again?")
    except Exception as e:
        await interaction.response.send_message(f"Unknown Error: {e}")



@app_commands.autocomplete(tz=IANA_autocomplete)
@client.tree.command(name="settimezone", description="Sets your timezone", guild=GUILD_ID)
@app_commands.describe(
  tz="Your timezone, in IANA format"
)
async def settimezone(interaction: discord.Interaction, tz: str):
    try:
        if tz not in TIMEZONES: 
            await interaction.response.send_message("Please select an IANA timezone from the drop-down menu")
            return
        if not (await client.db.getChannelID()):
            await interaction.response.send_message("Please set a channel to wish people in first!")
            return
        await client.db.writeTimezone(interaction.user.id, tz)

         # now update birthdays
        client.data_snapshot = await client.get_alldata() # get all current birthdays from the database
        client.midnights = client.get_midnights()

        if not client.birthdaycheck.is_running():
            client.birthdaycheck.start()
        
        client.birthdaycheck.change_interval(time = client.midnights)
        client.birthdaycheck.restart()
        print(f"restarted birthdaycheck {client.birthdaycheck.is_running()} {client.birthdaycheck.time}")
        await interaction.response.send_message(f"Your timezone is... {tz}.\nThis has been set in the database.")
    except Exception as e:
        await interaction.response.send_message(f"Unknown Error: {e}")


@client.tree.command(name="setchannel", description="set channel to wish a person in", guild=GUILD_ID)
@app_commands.describe(
    channel="channel used to send birthday messages in"
)
@app_commands.autocomplete(channel=client.get_channelnames)
async def setchannel(interaction: discord.Interaction, channel:str):
    try:
        my_id = None
        if GUILD_ID_INT:
            x = client.get_guild(GUILD_ID_INT)
            if x:
                for x in x.text_channels:
                    if x.name == channel:
                        my_id = x.id
        if my_id:
            await client.db.writechannelID(my_id)
            await interaction.response.send_message(f"channel id of {channel} is {my_id}. \n \
                                                I will now wish you happy birthday in this channel from here on out.")
            return
        else:
            await interaction.response.send_message(f"I can't find channel: {channel}, sorry!")
    except Exception as e:
        await interaction.response.send_message(f"Unknown Error: {e}")
# @client.tree.command(name="debugp", description = "Prints debug info", guild=GUILD_ID)
# async def debug(interaction: discord.Interaction):

#     await interaction.response.send_message(f"Your user ID is: {interaction.user.id}\n and your birthday is: {await client.db.getBirthday(interaction.user.id)}")


# # for debugging, remove later
# @client.tree.command(name="tabularasa", guild=GUILD_ID)
# async def purge(interaction: discord.Interaction):
#     await client.db.apurge() # type: ignore
#     await interaction.response.send_message(f"Purged database")




def main():
    if APIKEY:
        client.run(APIKEY)

if __name__ == "__main__":
    main()