from dataclasses import dataclass
from typing import Dict

@dataclass(init=False)
class NFT:
    template_id: int = None
    asset_id: str = None
    name: str = None
    schema_name: str = None



@dataclass(init=False)
class Yolasic(NFT):
    mutable_data: Dict = None
    schema_name = "asics"
    name = "YOLASIC"
    level: int = None
    rarity: str = None


@dataclass(init=False)
class YolasicFree(Yolasic):
    template_id = 490404
    rarity = "free"


@dataclass(init=False)
class YolasicCommon(Yolasic):
    template_id = 490405
    rarity = "common"

@dataclass(init=False)
class YolasicRare(Yolasic):
    template_id = 490415
    rarity = "rare"


@dataclass(init=False)
class YolasicEpic(Yolasic):
    template_id = 490416
    rarity = "epic"

@dataclass(init=False)
class YolasicLegendary(Yolasic):
    template_id = 490417
    rarity = "legendary"


@dataclass(init=False)
class YolasicCommon4(Yolasic):
    template_id = 552799
    rarity = "common"

@dataclass(init=False)
class YolasicRare4(Yolasic):
    template_id = 552800
    rarity = "rare"


@dataclass(init=False)
class YolasicEpic4(Yolasic):
    template_id = 552801
    rarity = "epic"

@dataclass(init=False)
class YolasicLegendary4(Yolasic):
    template_id = 552802
    rarity = "legendary"


yolasic_table = {
    "free": YolasicFree,
    "common": YolasicCommon,
    "rare": YolasicRare,
    "epic": YolasicEpic,
    "legendary": YolasicLegendary,
    "common4": YolasicCommon4,
    "rare4": YolasicRare4,
    "epic4": YolasicEpic4,
    "legendary4": YolasicLegendary4,
}

def get_card_class(rarity: str, card_class: int = 0):
    if card_class != 0:
        rarity = rarity + str(card_class)
    return yolasic_table[rarity]
