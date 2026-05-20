"""Backup utilities for feed data.

Handles exporting and restoring feed backups from JSON files.
"""

import json
import os
from datetime import datetime

from models.model_feeds import Feed
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.service_sqlalchemy import SQLAlchemy


class Backup:
    """Backup manager for feed data.

    Handles exporting feed records to JSON files and restoring from backups.
    """
    BACKUP_LOCATION = "/backups"
    FILENAME_FORMAT = "%Y-%m-%d.json"

    def __init__(self, filename=None):
        if self.validate_name(filename):
            self.filename = filename
        else:
            raise RuntimeError(f"Generated {filename=} is wrong")

    def __repr__(self) -> str:
        return f"<Backup filename='{self.filename}'>"

    @classmethod
    def today(cls):
        """Return the backup filename for today's date."""
        folder = cls.BACKUP_LOCATION
        date = datetime.now().strftime(cls.FILENAME_FORMAT)
        return f"{folder}/{date}"

    @classmethod
    def validate_name(cls, filename):
        """Validate a backup filename against expected folder and date pattern."""
        folder, file = filename.rsplit("/", 1)

        # check if filename is valid
        if folder != cls.BACKUP_LOCATION:
            return False
        try:
            datetime.strptime(file, cls.FILENAME_FORMAT)
        except ValueError:
            return False

        return True

    @classmethod
    def validate_file(cls, filename):
        """Validate that the backup file exists and contains valid JSON."""
        try:
            with open(filename, "r") as f:
                json.load(f)
        except FileNotFoundError:
            return False
        except json.decoder.JSONDecodeError:
            return False

        return True

    #############
    # BACKUP DUMP
    #############

    @staticmethod
    async def get_data(session: AsyncSession):
        """Retrieve all feed data from the database for backup export."""
        query = select(Feed)
        feeds = await SQLAlchemy.execute_all(
            query=query,
            session=session,
        )
        return [feed.as_dict() for feed in feeds]

    @classmethod
    async def dump(cls, session: AsyncSession):
        """Dump current feed data to today's backup file."""
        data = await cls.get_data(session)
        filename = cls.today()

        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

        return cls(
            filename=filename,
        )

    ################
    # BACKUP RESTORE
    ################

    @classmethod
    def list(cls):
        """List valid backup files in the backup folder."""
        items = []
        for filename in os.listdir(path=cls.BACKUP_LOCATION):
            filename = f"{ cls.BACKUP_LOCATION }/{ filename }"
            if cls.validate_name(filename) and cls.validate_file(filename):
                items.append(
                    cls(
                        filename=filename,
                    )
                )

        items.sort(reverse=False)

        return items

    async def restore(self, session: AsyncSession, compare=True):
        """Restore feed data from this backup file.

        Args:
            session: SQLAlchemy async session.
            compare: If True, compare backup content with current DB data.

        Returns:
            str: Restoration status message.
        """
        with open(self.filename) as f:
            json_data = json.load(f)
            if compare:
                if self.get_data() == json_data:
                    return "Backup data equals current DB data"
                else:
                    return "Data is different"
            else:
                for each in json_data:
                    feed = Feed(
                        title=each["title"],
                        href=each["href"],
                        href_user=each["href_user"],
                        private=each["private"],
                        frequency=each["frequency"],
                        notes=each["notes"],
                        json=each["json"],
                        _id=each["_id"],
                        _created=each["_created"],
                        _delayed=None,
                    )
                    session.add(feed)

                # await session.commit()

                return "Restoration complete"
