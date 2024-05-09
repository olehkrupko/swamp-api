import json
import os
from datetime import datetime

from config.db import db
from models.model_feeds import Feed


class Backup:
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
        folder = cls.BACKUP_LOCATION
        date = datetime.now().strftime(cls.FILENAME_FORMAT)
        return f"{folder}/{date}"

    @classmethod
    def validate_name(cls, filename):
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
        # check if file is valid
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
    def get_data():
        return [x.as_dict() for x in db.session.query(Feed).all()]

    @classmethod
    def dump(cls):
        data = cls.get_data()
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

    def restore(self, compare=True):
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
                    db.session.add(feed)

                db.session.commit()

                return "Restoration complete"
