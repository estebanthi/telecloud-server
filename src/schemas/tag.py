from dataclasses import dataclass
from bson import ObjectId


@dataclass
class Tag:
    _id: ObjectId
    name: str
    parent: ObjectId
    