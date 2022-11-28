from decimal import Decimal
import ruamel.yaml
yaml = ruamel.yaml.YAML()
from datetime import datetime
from ruamel.yaml.comments import CommentedMap
from settings import user_param

class recorder:
    min_price: Decimal = None
    min_time: datetime = None
    max_price: Decimal = None
    max_time: datetime = None

    @classmethod
    def update_price(cls, price: Decimal):
        if not user_param.record:
            return

        if not cls.min_price:
            cls.min_price = price
            cls.min_time = datetime.now()
        if not cls.max_price:
            cls.max_price = price
            cls.max_time = datetime.now()

        if price < cls.min_price:
            cls.min_price = price
            cls.min_time = datetime.now()

        if price > cls.max_price:
            cls.max_price = price
            cls.max_time = datetime.now()

        with open("price.txt", "w", encoding="utf8") as file:
            file.write("最高价格: {0}\n".format(cls.max_price.quantize(Decimal("0.0000000000"))))
            file.write("时间: {0}\n\n".format(cls.max_time.strftime("%Y-%m-%d %H:%M:%S")))
            file.write("最低价格: {0}\n".format(cls.min_price.quantize(Decimal("0.0000000000"))))
            file.write("时间: {0}\n".format(cls.min_time.strftime("%Y-%m-%d %H:%M:%S")))
