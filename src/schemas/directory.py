from dataclasses import dataclass
from bson import ObjectId


@dataclass
class Directory:
    _id: ObjectId
    name: str
    parent: ObjectId