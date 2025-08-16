# type: ignore
# pyright: ignore[reportUnknownMemberType]
from pickledb import AsyncPickleDB 
from typing import Any, Dict, List, Optional



DB_FILE_NAME = "birthday_data.db"

class BirthdayDB():
    def __init__(self) -> None:
        self.mydb = AsyncPickleDB(DB_FILE_NAME)

    def mydb(self) -> AsyncPickleDB:
        return self.mydb
    
    async def writeBirthday(self, userid: int, date: str, tz: str):
        await self.mydb.aset(userid, {"date": date, "tz": tz})
        result = await self.mydb.asave() 
        if not result:
            raise Exception("Database failed to save!")

    async def writeTimezone(self, userid: int, tz: str):
        userdata = await self.mydb.aget(userid)
        if not userdata["date"]:
            raise Exception("I have no date to save here! How do I wish you :(")
        await self.mydb.aset(userid, {"date":userdata["date"], "tz": tz})
        result = await self.mydb.asave() 
        if not result:
            raise Exception("Database failed to save!")

    async def writechannelID(self, channelid: int):
        await self.mydb.aset("channelid", channelid)
        result = await self.mydb.asave() 
        if not result:
            raise Exception("Database failed to save!")


    async def getKeys(self) -> List[int]:
        return await self.mydb.aall()
    
    async def getBirthday(self, userid: int) -> str:
        return await self.mydb.aget(userid)
    
    async def getChannelID(self) -> Optional[int]:
        return await int(self.mydb.aget("channelid"))

    async def apurge(self):
        await self.mydb.apurge()
        await self.mydb.asave()


# async def startup_db():
#     mydb = AsyncPickleDB(DB_FILE_NAME)
#     await mydb.aset("greeting", "hi") 
#     return mydb
    

# async def get_birthday(mydb: AsyncPickleDB) -> Dict[str, str]:
#     greeting = await mydb.aget("greeting") 
#     return greeting