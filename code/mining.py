import re
from datetime import datetime, timezone, timedelta
import time
from logger import log, _log
import logging
import requests
import functools
from eosapi import NodeException, TransactionException, EosApiException, Transaction
from eosapi import EosApi
from typing import List, Dict, Union, Tuple
from settings import user_param, interval
import tenacity
from tenacity import wait_fixed, RetryCallState, retry_if_not_exception_type, retry_if_exception_type
from requests import RequestException
from dataclasses import dataclass
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import schedule
from res import Yolasic, get_card_class
from utils import string_to_name
from record import recorder

version = "2.7.1"


class StopException(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)



@dataclass(init = False)
class Commodity:
    sale_id: str
    seller: str
    amount: int
    asset_id: int
    template_id: int
    price: Decimal




@dataclass
class HttpProxy:
    proxy: str
    user_name: str = None
    password: str = None

    def to_proxies(self) -> Dict:
        if self.user_name and self.password:
            proxies = {
                "http": "http://{0}:{1}@{2}".format(self.user_name, self.password, self.proxy),
                "https": "http://{0}:{1}@{2}".format(self.user_name, self.password, self.proxy),
            }
        else:
            proxies = {
                "http": "http://{0}".format(self.proxy),
                "https": "http://{0}".format(self.proxy),
            }
        return proxies


class Mining:

    def __init__(self, wax_account: str, private_key: str, proxy: HttpProxy = None):
        self.wax_account: str = wax_account
        self.log: logging.LoggerAdapter = logging.LoggerAdapter(_log, {"tag": self.wax_account})
        self.http = requests.Session()
        self.http.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, " \
                                          "like Gecko) Chrome/101.0.4951.54 Safari/537.36 "
        self.http.trust_env = False
        #self.http.verify = False
        self.http.request = functools.partial(self.http.request, timeout=120)
        self.rpc_host = user_param.rpc_domain
        self.eosapi = EosApi(self.rpc_host, timeout=120)
        self.eosapi.import_key(self.wax_account, private_key)
        if user_param.cpu_account and user_param.cpu_key:
            self.eosapi.set_cpu_payer(user_param.cpu_account, user_param.cpu_key)

        if proxy:
            proxies = proxy.to_proxies()
            self.http.proxies = proxies
            self.eosapi.session.proxies = proxies

        net_retry = tenacity.retry(retry = retry_if_exception_type(RequestException), wait=self.net_wait_retry)
        self.http.get = net_retry(self.http.get)
        self.http.post = net_retry(self.http.post)
        self.eosapi.session.get = net_retry(self.eosapi.session.get)
        self.eosapi.session.post = net_retry(self.eosapi.session.post)

        retry = tenacity.retry(retry = retry_if_not_exception_type(StopException), wait=self.wait_retry)
        self.getreward = retry(self.getreward)
        self.do_getreward = retry(self.do_getreward)
        self.stake = retry(self.stake)
        self.do_stake = retry(self.do_stake)
        self.unstake = retry(self.unstake)
        self.do_unstake = retry(self.do_unstake)
        self.scan_atomic = retry(self.scan_atomic)
        # self.do_upgrade = retry(self.do_upgrade)
        self.account_info = retry(self.account_info)
        self.executor = ThreadPoolExecutor(max_workers = user_param.threads)
        self.count_bought: int = 0
        self.count_bought_pack: int = 0
        self.next_buy_time: datetime = None

    def wait_retry(self, retry_state: RetryCallState) -> float:
        exp = retry_state.outcome.exception()
        wait_seconds = interval.transact
        if isinstance(exp, RequestException):
            self.log.info("网络错误: {0}".format(exp))
            wait_seconds = interval.net_error
        elif isinstance(exp, NodeException):
            self.log.info((str(exp)))
            self.log.info("节点错误,状态码【{0}】".format(exp.resp.status_code))
            wait_seconds = interval.transact
        elif isinstance(exp, TransactionException):
            self.log.info("交易失败： {0}".format(exp.resp.text))
            if "is greater than the maximum billable" in exp.resp.text:
                self.log.error("CPU资源不足，可能需要质押更多WAX，稍后重试")
                wait_seconds = interval.cpu_insufficient
            elif "is not less than the maximum billable CPU time" in exp.resp.text:
                self.log.error("交易被节点限制,可能被该节点拉黑")
                wait_seconds = interval.transact
        else:
            if exp:
                self.log.info("常规错误: {0}".format(exp), exc_info=exp)
            else:
                self.log.info("常规错误")
        self.log.info("{0}秒后重试: [{1}]".format(wait_seconds, retry_state.attempt_number))
        return float(wait_seconds)

    def net_wait_retry(self, retry_state: RetryCallState) -> float:
        exp = retry_state.outcome.exception()
        if isinstance(exp, RequestException):
            self.log.info("网络错误: {0}".format(exp))
            self.log.info("正在重试: [{0}]".format(retry_state.attempt_number))
        return float(interval.net_error)

    def scan_stake_cards(self) -> List[Dict]:
        self.log.info("正在扫描已质押的卡")
        all_rows = []
        next_key = ""
        while True:
            post_data = {
                "json": True,
                "code": "miningntwrkc",
                "scope": self.wax_account,
                "table": "stakedassets",
                "lower_bound": next_key,
                "upper_bound": "",
                "index_position": 1,
                "key_type": "i64",
                "limit": 10000,
                "reverse": False,
                "show_payer": False
            }
            resp = self.eosapi.get_table_rows(post_data)
            if len(resp["rows"]) <= 0:
                break
            all_rows.extend(resp["rows"])
            self.log.info("扫描[{0}]".format(len(all_rows)))
            if not resp["next_key"]:
                break
            next_key = resp["next_key"]
            time.sleep(2)
        self.log.info("一共{0}张已经质押的卡".format(len(all_rows)))
        return all_rows

    def do_upgrade(self):
        self.log.info("准备升级卡")
        stake_cards = self.scan_stake_cards()

        yolasic_cls = get_card_class(user_param.rarity, user_param.card_class)
        time_now = datetime.now()
        for item in stake_cards.copy():
            last_claim_time = datetime.fromtimestamp(int(item["last_claim_time"]))
            if item["template_id"] != yolasic_cls.template_id:
                stake_cards.remove(item)
            elif item["level"] >= item["max_level"]:
                stake_cards.remove(item)
            elif item["level"] >= user_param.level:
                stake_cards.remove(item)
            elif last_claim_time >= time_now:
                stake_cards.remove(item)

        self.log.info(f"其中{len(stake_cards)}张{user_param.rarity}卡可以升到{user_param.level}级")

        if len(stake_cards) <= 0:
            return False

        if 0 < user_param.max_count < len(stake_cards):
            stake_cards = stake_cards[:user_param.max_count]
            self.log.info("根据设置最多升级{0}张卡".format(len(stake_cards)))

        self.log.info(f"准备将{len(stake_cards)}张{user_param.rarity}卡升到{user_param.level}级")
        asset_ids = [item["asset_id"] for item in stake_cards]
        count = 0
        for item in asset_ids:
            if self.upgrade(item, user_param.level):
                count += 1
            time.sleep(interval.req)

        self.log.info("升级成功{0}张卡".format(count))

    def upgrade(self, asset_id: str, level: int) -> bool:
        self.log.info("开始升级卡:{0}到{1}级".format(asset_id, level))
        trx = {
            "actions": [{
                "account": "miningntwrkc",
                "name": "upgrade",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "owner": self.wax_account,
                    "asset_id": str(asset_id),
                    "level": level,
                }}]
        }
        try:
            resp = self.eosapi.push_transaction(trx)
            self.log.info("交易成功:{0}".format(resp["transaction_id"]))
            return True
        except RequestException as e:
            self.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            self.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            self.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
            if "is greater than the maximum billable" in e.resp.text:
                self.log.error("CPU资源不足，可能需要质押更多WAX，稍后重试")
            elif "is not less than the maximum billable CPU time" in e.resp.text:
                self.log.error("交易被节点限制,可能被该节点拉黑")
        return False


    def do_speed_up(self):
        self.log.info("准备加速升级卡")
        stake_cards = self.scan_stake_cards()

        yolasic_cls = get_card_class(user_param.rarity, user_param.card_class)
        time_now = datetime.now()
        for item in stake_cards.copy():
            last_claim_time = datetime.fromtimestamp(int(item["last_claim_time"]))
            if item["template_id"] != yolasic_cls.template_id:
                stake_cards.remove(item)
            elif last_claim_time < time_now:
                stake_cards.remove(item)

        self.log.info(f"其中{len(stake_cards)}张{user_param.rarity}卡可以加速升级")

        if len(stake_cards) <= 0:
            return False

        if 0 < user_param.max_count < len(stake_cards):
            stake_cards = stake_cards[:user_param.max_count]
            self.log.info("根据设置最多加速升级{0}张卡".format(len(stake_cards)))

        self.log.info(f"准备将{len(stake_cards)}张{user_param.rarity}卡加速升级")
        asset_ids = [item["asset_id"] for item in stake_cards]
        count = 0
        for item in asset_ids:
            if self.speed_up(item):
                count += 1
            time.sleep(interval.req)

        self.log.info("加速升级成功{0}张卡".format(count))


    def speed_up(self, asset_id: str) -> bool:
        self.log.info("开始加速升级卡:{0}".format(asset_id))
        trx = {
            "actions": [{
                "account": "miningntwrkc",
                "name": "speedupgrade",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "owner": self.wax_account,
                    "asset_id": str(asset_id),
                }}]
        }
        try:
            resp = self.eosapi.push_transaction(trx)
            self.log.info("交易成功:{0}".format(resp["transaction_id"]))
            return True
        except RequestException as e:
            self.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            self.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            self.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
            if "is greater than the maximum billable" in e.resp.text:
                self.log.error("CPU资源不足，可能需要质押更多WAX，稍后重试")
            elif "is not less than the maximum billable CPU time" in e.resp.text:
                self.log.error("交易被节点限制,可能被该节点拉黑")
        return False


    def scan_assets(self, schema_name: str = None, template_id: int = None) -> List[Dict]:
        self.log.info("正在扫描NFT")
        url_assets = user_param.rpc_atomic + "/atomicassets/v1/assets"
        page = 0
        assets = []
        while True:
            page += 1
            payload = {
                "page": page,
                "limit": 1000,
                "collection_name": "miningntwrkc",
                "owner": self.wax_account,
                "hide_offers": 1,
            }
            if schema_name:
                payload["schema_name"] =schema_name
            if template_id:
                payload["template_id"] = template_id
            resp = self.http.get(url_assets, params = payload)
            if resp.status_code != 200:
                raise NodeException("原子节点错误", resp)
            resp = resp.json()

            assets.extend(resp["data"])
            if len(resp) < 1000:
                break
        return assets


    def scan_nft_yolasic(self, yolasic_cls: type[Yolasic]) -> List[Yolasic]:
        assets = self.scan_assets(template_id = yolasic_cls.template_id)
        all_yolasic = []
        for item in assets:
            yolasic = yolasic_cls()
            yolasic.asset_id = item["asset_id"]
            yolasic.level = item["data"].get("level", 0)
            yolasic.mutable_data = item["mutable_data"]
            all_yolasic.append(yolasic)
        return all_yolasic


    def do_stake(self):
        self.log.info("准备质押卡")
        cards = self.filter_nft_yolasic()
        if len(cards) <= 0:
            return False

        asset_ids = [item.asset_id for item in cards]
        group_count = 50
        for i in range(0, len(asset_ids), group_count):
            if len(asset_ids) - i <= group_count:
                sub = asset_ids[i:]
            else:
                sub = asset_ids[i: i + group_count]
            self.stake(sub)
            time.sleep(2)

    def stake(self, asset_ids: List[str]) -> bool:
        self.log.info("开始质押{0}张卡".format(len(asset_ids)))
        trx = {
            "actions": []
        }

        for item in asset_ids:
            action = {
                "account": "atomicassets",
                "name": "transfer",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "from": self.wax_account,
                    "to": "miningntwrkc",
                    "asset_ids": [str(item)],
                    "memo": "stake",
                },
            }
            trx["actions"].append(action)

        resp = self.eosapi.push_transaction(trx)
        self.log.info("交易成功:{0}".format(resp["transaction_id"]))
        return True

    def do_unstake(self):
        self.log.info("准备解除质押卡")
        stake_cards = self.scan_stake_cards()

        time_now = datetime.now()
        for item in stake_cards.copy():
            last_claim_time = datetime.fromtimestamp(int(item["last_claim_time"]))
            if last_claim_time >= time_now:
                stake_cards.remove(item)

        self.log.info("其中{0}张卡可以解除质押".format(len(stake_cards)))

        yolasic_cls = get_card_class(user_param.rarity, user_param.card_class)
        for item in stake_cards.copy():
            if item["template_id"] != yolasic_cls.template_id:
                stake_cards.remove(item)

        self.log.info(f"其中{len(stake_cards)}张{user_param.rarity}卡可以解除质押")

        if user_param.level >= 0:
            for item in stake_cards.copy():
                if int(item["level"]) != user_param.level:
                    stake_cards.remove(item)
            self.log.info(f"其中{len(stake_cards)}张{user_param.level}级{user_param.rarity}卡可以解除质押")

        if 0 < user_param.max_count < len(stake_cards):
            stake_cards = stake_cards[:user_param.max_count]
            self.log.info("根据设置最多解除质押{0}张卡".format(len(stake_cards)))

        asset_ids = [item["asset_id"] for item in stake_cards]
        group_count = 50
        for i in range(0, len(asset_ids), group_count):
            if len(asset_ids) - i <= group_count:
                sub = asset_ids[i:]
            else:
                sub = asset_ids[i: i + group_count]
            self.unstake(sub)
            time.sleep(2)

    def unstake(self, asset_ids: List[str]) -> bool:
        self.log.info("开始解除质押{0}张卡".format(len(asset_ids)))
        trx = {
            "actions": []
        }

        for item in asset_ids:
            action = {
                "account": "miningntwrkc",
                "name": "unstake",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "owner": self.wax_account,
                    "asset_id": str(item),
                },
            }
            trx["actions"].append(action)

        resp = self.eosapi.push_transaction(trx)
        self.log.info("交易成功:{0}".format(resp["transaction_id"]))
        return True

    def getreward(self, asset_ids: List[str]) -> bool:
        self.log.info("开始收集{0}张卡的奖励".format(len(asset_ids)))
        trx = {
            "actions": [{
                "account": "miningntwrkc",
                "name": "getreward",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "owner": self.wax_account,
                    "asset_ids": asset_ids,
                }}]
        }
        resp = self.eosapi.push_transaction(trx)
        self.log.info("交易成功:{0}".format(resp["transaction_id"]))
        return True

    def do_getreward(self):
        self.log.info("开始收集奖励")
        all_rows = self.scan_stake_cards()
        asset_ids = [item["asset_id"] for item in all_rows]
        count_group = user_param.group
        for i in range(0, len(asset_ids), count_group):
            if len(asset_ids) - i <= count_group:
                sub = asset_ids[i:]
            else:
                sub = asset_ids[i: i + count_group]
            self.getreward(sub)
            time.sleep(interval.req)
        if user_param.withdraw:
            self.log.info("2分钟后兑换成BTK")
            time.sleep(120)
            for i in range(0, 10):
                if self.withdraw_sh_to_btk():
                    break
                if i < 10:
                    self.log.info("稍后重试")
                    time.sleep(interval.transact)
        if user_param.collect:
            self.log.info("2分钟后归集BTK")
            time.sleep(120)
            btk = self.balance_btk()
            if btk >= Decimal("0.01"):
                self.transfer_btk(user_param.account, btk)
            else:
                self.log.info("BTK余额过少，不归集")
        self.log.info("收集完毕，{0}分钟后再收集".format(user_param.getreward))


    def keep_getreward(self):
        schedule.every(user_param.getreward).minutes.do(self.do_getreward)
        schedule.run_all()
        while True:
            schedule.run_pending()
            time.sleep(1)

    def buy(self, dity: Commodity):
        self.log.info("正在购买:{0}".format(dity))
        price = "{0} WAX".format(dity.price.quantize(Decimal("0.00000000")))
        action1 = {
            "account": "atomicmarket",
            "name": "assertsale",
            "authorization": [{
                "actor": self.wax_account,
                "permission": "active",
            }],
            "data": {
                "sale_id": dity.sale_id,
                "asset_ids_to_assert": [str(dity.asset_id)],
                "listing_price_to_assert": price,
                "settlement_symbol_to_assert": "8,WAX"
            }
        }

        action2 = {
            "account": "eosio.token",
            "name": "transfer",
            "authorization": [{
                "actor": self.wax_account,
                "permission": "active",
            }],
            "data": {
                "from": self.wax_account,
                "to": "atomicmarket",
                "quantity": price,
                "memo": "deposit"
            }
        }

        action3 = {
            "account": "atomicmarket",
            "name": "purchasesale",
            "authorization": [{
                "actor": self.wax_account,
                "permission": "active",
            }],
            "data": {
                "buyer": self.wax_account,
                "sale_id": dity.sale_id,
                "intended_delphi_median": 0,
                "taker_marketplace": ""
            }
        }

        trx = {"actions": [action1, action2, action3]}

        try:
            resp = self.eosapi.push_transaction(trx)
            self.log.info("交易成功:{0}".format(resp["transaction_id"]))
            return True
        except RequestException as e:
            self.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            self.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            self.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        return False


    def scan_atomic(self, rarity: str = None, level: int = -1) -> List[Commodity]:
        rarity_text = rarity if rarity else ""
        level_text = "{0}级".format(level) if level >= 0 else "所有等级"
        self.log.info(f"开始扫描原子市场上的{level_text}{rarity_text}卡")
        url = user_param.rpc_atomic + "/atomicmarket/v2/sales"
        payload = {
            "collection_name": "miningntwrkc",
            "contract_whitelist": "theonlykarma,sales.heroes,niftywizards,cc32dninenft",
            "limit": 100,
            "order": "asc",
            "page": 1,
            "schema_name": "asics",
            "seller_blacklist": "dximg.wam,xpvrs.wam,5rrrc.wam,nnmnmnmnn.gm",
            "sort": "price",
            "state": 1,
            "symbol": "WAX"
        }
        if level >= 0:
            payload["mutable_data:number.level"] = level
        if rarity:
            payload["template_data:text.rarity"] = rarity

        resp = self.http.get(url, params=payload)
        resp = resp.json()

        ditys = []
        data: List[Dict] = resp["data"]
        for item in data:
            dity = Commodity()
            dity.sale_id = item["sale_id"]
            dity.seller = item["seller"]
            price = item["price"]
            if price["token_symbol"] != "WAX":
                continue
            if price["token_precision"] != 8:
                continue
            dity.amount = int(price["amount"])
            dity.price = Decimal(price["amount"]) / Decimal(100000000)
            dity.price = dity.price.quantize(Decimal("0.00000000"))

            assets = item["assets"]
            if len(assets) != 1:
                continue
            if assets[0]["schema"]["schema_name"] != "asics":
                continue
            dity.template_id = int(assets[0]["template"]["template_id"])
            dity.asset_id = assets[0]["asset_id"]
            ditys.append(dity)
            self.log.info(dity)


        self.log.info("一共扫描出{0}张".format(len(ditys)))
        return ditys



    def do_buy(self) -> bool:
        continue_buy = True
        limit_price = Decimal(user_param.limit_price)
        self.log.info("开始一轮扫货")
        ditys = self.scan_atomic(user_param.rarity, user_param.level)
        self.log.info("限制价格:{0}".format(limit_price))
        self.log.info("开始购买")

        count = 0
        futures = []
        for item in ditys:
            if item.price <= limit_price:
                futures.append(self.executor.submit(self.buy, item))
                self.count_bought += 1
                if self.count_bought >= user_param.max_count > 0:
                    break

        for item in futures:
            if item.result():
                count += 1
            else:
                self.count_bought -= 1

        if self.count_bought >= user_param.max_count > 0:
            self.log.info("达到购买数量，停止购买")
            continue_buy = False

        self.log.info("本轮成功购买{0}张".format(count))
        self.log.info("累计成功购买{0}张".format(self.count_bought))
        return continue_buy


    def keep_buy(self):
        self.count_bought = 0
        while True:
            if not self.do_buy():
                break
            self.log.info("10秒后开始下一轮扫货")
            time.sleep(10)
        self.log.info("扫货完毕，退出")


    def sell(self, asset_id: str, price: Decimal) -> bool:
        self.log.info("开始挂单【{0}】价格【{1}】".format(asset_id, price))
        trx = {
            "actions": [{
                "account": "atomicmarket",
                "name": "announcesale",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "seller": self.wax_account,
                    "asset_ids": [asset_id],
                    "listing_price": "{0} WAX".format(price.quantize(Decimal("0.00000000"))),
                    "settlement_symbol": "8,WAX",
                    "maker_marketplace": "",
                }}, {
                "account": "atomicassets",
                "name": "createoffer",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "sender": self.wax_account,
                    "recipient": "atomicmarket",
                    "sender_asset_ids": [asset_id],
                    "recipient_asset_ids": [],
                    "memo": "sale",
                }}, ]
        }
        try:
            resp = self.eosapi.push_transaction(trx)
            self.log.info("交易成功:{0}".format(resp["transaction_id"]))
            return True
        except RequestException as e:
            self.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            self.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            self.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        return False


    def trans_assets(self, to_account: str, asset_ids: List[str]):
        trx = {
            "actions": [{
                "account": "atomicassets",
                "name": "transfer",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "from": self.wax_account,
                    "to": to_account,
                    "asset_ids": asset_ids,
                    "memo": "",
                },
            }]
        }
        try:
            resp = self.eosapi.push_transaction(trx)
            self.log.info("交易成功:{0}".format(resp["transaction_id"]))
            return True
        except RequestException as e:
            self.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            self.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            self.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        return False


    def transfer(self):
        cards = self.filter_nft_yolasic()
        if len(cards) <= 0:
            return False

        while True:
            text = input(f"准备转移【{ len(cards) }】张{cards[0].rarity}卡到账户【{ user_param.to_account }】,请输入ok并按回车确认:")
            if text == "ok":
                break
        self.log.info(f"正在转移【{ len(cards) }】张{cards[0].rarity}卡到账户【{ user_param.to_account }】")
        asset_ids = [item.asset_id for item in cards]
        self.trans_assets(user_param.to_account, asset_ids)


    def filter_nft_yolasic(self):
        yolasic_cls = get_card_class(user_param.rarity, user_param.card_class)
        all_yolasic = self.scan_nft_yolasic(yolasic_cls)
        self.log.info(f"一共{ len(all_yolasic) }张class{user_param.card_class}的{ yolasic_cls.rarity }卡".format())

        if user_param.level >= 0:
            for item in all_yolasic.copy():
                if item.level != user_param.level:
                    all_yolasic.remove(item)
            self.log.info(f"一共{ len(all_yolasic) }张{ user_param.level }等级的{ yolasic_cls.rarity }卡")

        if 0 < user_param.max_count < len(all_yolasic):
            all_yolasic = all_yolasic[:user_param.max_count]
            self.log.info(f"根据设置最多处理{ len(all_yolasic) }张卡")

        return all_yolasic



    def do_sell(self):
        cards = self.filter_nft_yolasic()
        if len(cards) <= 0:
            return False

        sell_price = Decimal(user_param.sell_price)
        if user_param.level >= 0:
            text = input(f"准备挂单【{ len(cards) }】张【{ user_param.level }】等级的{ cards[0].rarity }卡到原子市场，价格【{sell_price}】一张,请按回车键确认:")
        else:
            text = input(f"准备挂单【{len(cards)}】张{cards[0].rarity}卡到原子市场，价格【{sell_price}】一张,请按回车键确认:")
        count = 0
        for item in cards:
            if self.sell(item.asset_id, sell_price):
                count += 1
        self.log.info("成功挂单{0}张".format(count))


    def account_info(self) -> List[Dict]:
        self.log.info("正在获取账户信息")
        post_data = {
            "json": True,
            "code": "miningntwrkc",
            "scope": "miningntwrkc",
            "table": "accounts",
            "lower_bound": self.wax_account,
            "upper_bound": self.wax_account,
            "index_position": 1,
            "key_type": "name",
            "limit": 1,
            "reverse": False,
            "show_payer": False
        }
        resp = self.eosapi.get_table_rows(post_data)
        if len(resp["rows"]) != 1:
            return None
        return resp["rows"][0]



    def buy_pack(self):
        self.log.info("买包时间到，开始买包")
        trx = {
            "actions": [{
                "account": "miningntwrkt",
                "name": "transfer",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "from": self.wax_account,
                    "to": "miningntwrkc",
                    "quantity": "50.0000 BTK",
                    "memo": "buy:{0}".format(552798),
                },
            }]
        }
        try:
            resp = self.eosapi.push_transaction(trx)
            self.log.info("交易成功:{0}".format(resp["transaction_id"]))
            success = True
        except RequestException as e:
            self.log.info("网络错误:{0}".format(str(e)))
            success = False
        except NodeException as e:
            self.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
            success = False
        except TransactionException as e:
            self.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
            success = False
        except Exception as e:
            self.log.exception("其它错误: {0}".format(str(e)))
            success = False

        if success:
            self.count_bought_pack += 1
            self.next_buy_time = datetime.now() + timedelta(minutes=30) + timedelta(seconds=5)
        return success


    def do_buy_pack(self):
        if self.is_ready_buy_pack():
            time.sleep(interval.req)
            return self.buy_pack()
        else:
            return False


    def is_ready_buy_pack(self):
        self.log.info("准备买包")
        # 查询上次采矿的信息
        info = self.check_signup()
        if not info:
            raise StopException("获取账户信息失败")
        last_bought_time = datetime.fromtimestamp(info["last_bought_at"])
        self.log.info("上次买包时间: {0}".format(last_bought_time))
        ready_buy_time = last_bought_time + timedelta(minutes=30)
        if datetime.now() < ready_buy_time:
            self.next_buy_time = ready_buy_time + timedelta(seconds=5)
            self.log.info("买包时间不到,下次买包时间: {0}".format(self.next_buy_time))
            return False
        else:
            self.next_buy_time = ready_buy_time
            return True


    def keep_buy_pack(self):
        self.count_bought_pack = 0
        if user_param.max_count > 0:
            self.log.info("根据设置最多买{0}个包".format(user_param.max_count))
        else:
            self.log.info("根据设置将不限数量一直买包")
        self.do_buy_pack()
        while True:
            if datetime.now() > self.next_buy_time:
                self.do_buy_pack()
                if self.count_bought_pack >= user_param.max_count > 0:
                    self.log.info("根据设置最多买{0}个包，停止购买".format(user_param.max_count))
                    break
                else:
                    self.log.info("累计购买{0}个包,30分钟后再买".format(self.count_bought_pack))
            time.sleep(1)


    def unpack_and_cliam(self, asset_id: str):
        if not self.unpack(asset_id):
            return False
        self.log.info("等待领取")
        time.sleep(10)
        pack_assets = self.query_pack_assets()
        if not pack_assets:
            self.log.info("开包出错，pack_assets不存在")
            raise StopException("开包出错，pack_assets不存在")
        time.sleep(10)
        count = 0
        for item in pack_assets:
            if self.claim_pack(item["pack_asset_id"]):
                count += 1
            time.sleep(2)
        return True if count > 0 else False

    def unpack(self, asset_id: str):
        self.log.info("正在开包:{0}".format(asset_id))
        trx = {
            "actions": [{
                "account": "atomicassets",
                "name": "transfer",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "from": self.wax_account,
                    "to": "atomicpacksx",
                    "asset_ids": [asset_id],
                    "memo": "unbox",
                },
            }]
        }
        try:
            resp = self.eosapi.push_transaction(trx)
            self.log.info("交易成功:{0}".format(resp["transaction_id"]))
            return True
        except RequestException as e:
            self.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            self.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            self.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        return False


    def do_unpack(self):
        self.log.info("准备开包")
        success = False
        pack_assets = self.query_pack_assets()
        if pack_assets:
            self.log.info("还有{0}个已开包但未领取的卡".format(len(pack_assets)))
            for item in pack_assets:
                if self.claim_pack(item["pack_asset_id"]):
                    success = True
                time.sleep(interval.req)
        time.sleep(interval.req)
        assets = self.scan_assets(template_id = 534070)
        self.log.info("一共有{0}个包".format(len(assets)))
        if len(assets) <= 0:
            return True if success else False

        if 0 < user_param.max_count < len(assets):
            assets = assets[:user_param.max_count]
            self.log.info("根据设置最多开{0}个包".format(len(assets)))

        count = 0
        for item in assets:
            if self.unpack_and_cliam(item["asset_id"]):
                count += 1
            time.sleep(interval.req)
        self.log.info("成功开包{0}个".format(count))
        return True



    def query_pack_assets(self) -> List[Dict]:
        uint64_name = string_to_name(self.wax_account)
        post_data = {
            "json": True,
            "code": "atomicpacksx",
            "scope": "atomicpacksx",
            "table": "unboxpacks",
            "lower_bound": str(uint64_name),
            "upper_bound": str(uint64_name),
            "index_position": "2",
            "key_type": "i64",
            "limit": 1000,
            "reverse": False,
            "show_payer": False
        }
        resp = self.eosapi.get_table_rows(post_data)
        if len(resp["rows"]) <= 0:
            return None
        return resp["rows"]


    def claim_pack(self, pack_asset_id: str):
        self.log.info("正在领取包内卡片:{0}".format(pack_asset_id))
        trx = {
            "actions": [{
                "account": "atomicpacksx",
                "name": "claimunboxed",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "pack_asset_id": pack_asset_id,
                    "origin_roll_ids": [0],
                },
            }]
        }
        try:
            resp = self.eosapi.push_transaction(trx)
            self.log.info("交易成功:{0}".format(resp["transaction_id"]))
            return True
        except RequestException as e:
            self.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            self.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            self.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        return False


    def signup(self):
        self.log.info("正在注册游戏账号")
        trx = {
            "actions": [{
                "account": "miningntwrkc",
                "name": "signup",
                "authorization": [{
                    "actor": self.wax_account,
                    "permission": "active",
                }],
                "data": {
                    "user": self.wax_account,
                    "referrer": "",
                },
            }]
        }
        resp = self.eosapi.push_transaction(trx)
        self.log.info("交易成功:{0}".format(resp["transaction_id"]))
        return True


    def transfer_btk(self, to_account: str, amount: Decimal):
        self.log.info(f"正在从账户【{self.wax_account}】转账【{amount}】个BTK到账户【{to_account}】")
        quantity = "{0} BTK".format(amount.quantize(Decimal("0.0000")))
        trx = {
            "actions": [{
                "account": "miningntwrkt",
                "name": "transfer",
                "authorization": [
                    {
                        "actor": self.wax_account,
                        "permission": "active",
                    },
                ],
                "data": {
                    "from": self.wax_account,
                    "to": to_account,
                    "quantity": quantity,
                    "memo": "",
                },
            }]
        }
        resp = self.eosapi.push_transaction(trx)
        self.log.info("交易成功:{0}".format(resp["transaction_id"]))
        return True


    def check_signup(self):
        info = self.account_info()
        if not info:
            self.log.info("游戏账号未注册")
            self.signup()
            time.sleep(interval.req)
            info = self.account_info()
        return info

    def transfer_all_yolasic(self, to_account: str):
        assets = self.scan_assets(schema_name = "asics")
        self.log.info(f"一共{ len(assets) }张卡片")
        if len(assets) <= 0:
            return False
        assets = [item["asset_id"] for item in assets]
        self.log.info(f"正在转移【{ len(assets) }】张卡到账户【{ to_account }】")
        return self.trans_assets(to_account, assets)


    def balance_btk(self):
        self.log.info("正在查询账户余额")
        url = self.rpc_host + "/v1/chain/get_currency_balance"
        post_data = {
            "account": self.wax_account,
            "code": "miningntwrkt",
            "symbol": "BTK",
        }
        resp = self.http.post(url, json = post_data)
        if resp.status_code != 200:
            raise NodeException("节点错误", resp)
        resp = resp.json()
        if len(resp) <= 0:
            btk = Decimal(0)
        else:
            btk = Decimal(resp[0].split(" ")[0])
        self.log.info(f"账户余额 {btk} BTK")
        return btk


    def query_pool(self):
        self.log.info("正在查询价格信息")
        post_data = {
            "json": True,
            "code": "miningntwrkc",
            "scope": "miningntwrkc",
            "table": "config",
            "lower_bound": "",
            "upper_bound": "",
            "index_position": 1,
            "key_type": "i64",
            "limit": 1,
            "reverse": False,
            "show_payer": False
        }
        resp = self.eosapi.get_table_rows(post_data)
        if len(resp["rows"]) != 1:
            raise StopException("无法查询价格信息: {0}".format(resp))
        return resp["rows"][0]


    def trx_sh_to_btk(self, sh_balance: Decimal, min_price: Decimal):
        self.log.info(f"正在将 {sh_balance} SH兑换成BTK")
        btk = sh_balance * min_price * Decimal("0.0001") * Decimal("0.95")
        btk = btk.quantize(Decimal("0.0000"))
        trx = {
            "actions": [{
                "account": "miningntwrkc",
                "name": "withdraw",
                "authorization": [
                    {
                        "actor": self.wax_account,
                        "permission": "active",
                    },
                ],
                "data": {
                    "owner": self.wax_account,
                    "amount": int(sh_balance),
                    "min_receive": "{0} BTK".format(btk),
                },
            }]
        }
        try:
            resp = self.eosapi.push_transaction(trx)
            self.log.info("交易成功:{0}".format(resp["transaction_id"]))
            return True
        except RequestException as e:
            self.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            self.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            self.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        return False


    def withdraw_sh_to_btk(self):
        sh2btk_price, btk2sh_price, min_price = self.query_exchange_price()
        time.sleep(interval.req)
        info = self.account_info()
        time.sleep(interval.req)
        if not info:
            raise StopException("无法获取账户信息")
        sh_balance = Decimal(info["balance"])
        self.log.info(f"SH余额: { sh_balance }")
        if sh_balance < 10000000000:
            self.log.info("SH过少，暂不兑换")
            return True
        return self.trx_sh_to_btk(sh_balance, min_price)


    def query_exchange_price(self) -> Tuple[Decimal, Decimal, Decimal]:
        pool = self.query_pool()
        tokens_pool = Decimal(pool["tokens_pool"])
        shares_pool = Decimal(pool["shares_pool"])
        inflation_amount = Decimal(50000)
        btk2sh_price = (tokens_pool + inflation_amount) / shares_pool
        #btk2sh_price = Decimal(1) / price / Decimal("0.0001")
        inflation_amount = Decimal(80000)
        sh2btk_price = (tokens_pool + inflation_amount) / shares_pool
        #sh2btk_price = Decimal(1) / price / Decimal("0.0001")
        inflation_amount = Decimal(0)
        min_price = (tokens_pool + inflation_amount) / shares_pool
        #min_price = Decimal(1) / price / Decimal("0.0001")
        return sh2btk_price, btk2sh_price, min_price


    def do_sh2btk(self):
        sh2btk_price, btk2sh_price, min_price = self.query_exchange_price()
        self.log.info(f"当前价格: 10000 SH = {sh2btk_price} BTK")
        recorder.update_price(sh2btk_price)
        if sh2btk_price < Decimal(user_param.sh_price):
            self.log.info(f"没有达到预期价格: 10000 SH = {user_param.sh_price} BTK")
            return False
        self.log.info(f"达到预期价格: 10000 SH = {user_param.sh_price} BTK")

        info = self.account_info()
        time.sleep(interval.req)
        if not info:
            raise StopException("无法获取账户信息")
        sh_balance = Decimal(info["balance"])
        self.log.info(f"SH余额: {sh_balance}")
        if sh_balance < 100000:
            self.log.info("SH过少，暂不兑换")
            return False

        return self.trx_sh_to_btk(sh_balance, min_price)

    def keep_sh2btk(self):
        self.log.info("开始将SH兑换为BTK")
        schedule.every(user_param.interval_price).seconds.do(self.do_sh2btk)
        schedule.run_all()
        while True:
            schedule.run_pending()
            time.sleep(1)


    def trx_btk_to_sh(self, btk_balance: Decimal, sh_number: Decimal):
        btk_balance = btk_balance.quantize(Decimal("0.0000"))
        self.log.info(f"正在将 {btk_balance} BTK兑换成SH")
        trx = {
            "actions": [{
                "account": "miningntwrkt",
                "name": "transfer",
                "authorization": [
                    {
                        "actor": self.wax_account,
                        "permission": "active",
                    },
                ],
                "data": {
                    "from": self.wax_account,
                    "to": "miningntwrkc",
                    "quantity": "{0} BTK".format(btk_balance),
                    "memo": "swap:{0}".format(int(sh_number))
                },
            }]
        }
        try:
            resp = self.eosapi.push_transaction(trx)
            self.log.info("交易成功:{0}".format(resp["transaction_id"]))
            return True
        except RequestException as e:
            self.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            self.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            self.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        return False


    def do_btk2sh(self):
        sh2btk_price, btk2sh_price, min_price = self.query_exchange_price()
        self.log.info(f"当前价格: 10000 SH = {btk2sh_price} BTK")
        recorder.update_price(btk2sh_price)
        if btk2sh_price > Decimal(user_param.sh_price):
            self.log.info(f"没有达到预期价格: 10000 SH = {user_param.sh_price} BTK")
            return False
        self.log.info(f"达到预期价格: 10000 SH = {user_param.sh_price} BTK")

        btk = self.balance_btk()
        time.sleep(interval.req)
        if btk < Decimal("0.1"):
            self.log.info("BTK过少，暂不兑换")
            return False

        sh_number = (btk / btk2sh_price) * Decimal(10000)
        return self.trx_btk_to_sh(btk, sh_number)


    def keep_btk2sh(self):
        self.log.info("开始将BTK兑换为SH")
        schedule.every(user_param.interval_price).seconds.do(self.do_btk2sh)
        schedule.run_all()
        while True:
            schedule.run_pending()
            time.sleep(1)

    def test(self):
        self.withdraw_sh_to_btk()
