from typing import List, Dict, Optional
from dataclasses import dataclass
from dacite import from_dict, Config
from decimal import Decimal

class interval:
    # HTTP请求间隔
    req: int = 2
    # 网络错误
    net_error: int = 5
    # 常规交易错误
    transact: int = 10
    # cpu不足
    cpu_insufficient: int = 30
    # 交易最大错误次数，超过终止程序
    max_trx_error: int = 5

@dataclass
class UserParam:
    rpc_domain: str = "https://wax.pink.gg"
    rpc_atomic: str = "https://aa.dapplica.io"

    proxy: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None

    cpu_account: Optional[str] = None
    cpu_key: Optional[str] = None

    account: str = None
    private_key: str = None

    sub_accounts: Optional[Dict[str, str]] = None

    rarity: str = None
    card_class: int = 0
    max_count: int = 0
    level: int = 0

    getreward: int = 60
    withdraw: bool = False
    collect: bool = False
    group: int = 500

    threads: int = 1
    limit_price: str = None

    to_account: str = None

    sell_price: str = None
    sh_price: str = None
    interval_price: int = 60
    record: Optional[bool] = False




user_param: UserParam = UserParam()


def load_param(data: Dict) -> UserParam:
    user = from_dict(UserParam, data, config = Config(type_hooks={str: str}))
    user_param.__dict__ = user.__dict__
