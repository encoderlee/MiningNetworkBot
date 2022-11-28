import time
import logger
from logger import log
import ruamel.yaml
yaml = ruamel.yaml.YAML()
from ruamel.yaml.comments import CommentedMap
from settings import user_param, load_param, interval
import argparse
from mining import HttpProxy, Mining, StopException, version
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, Future
from decimal import Decimal
from requests import RequestException
from eosapi import NodeException, TransactionException


class Batch:
    def __init__(self):
        self.main_account: Mining = None
        self.sub_accounts: List[Mining] = None
        self.executor = ThreadPoolExecutor(max_workers=user_param.threads)

    def do_buy_pack(self, miner: Mining) -> bool:
        try:
            miner.log.info(f"开始使用账号【{miner.wax_account}】买包")
            miner.check_signup()
            time.sleep(interval.req)
            if not miner.is_ready_buy_pack():
                return False
            time.sleep(interval.req)
            btk = miner.balance_btk()
            time.sleep(interval.req)
            if btk < Decimal("25"):
                self.main_account.transfer_btk(miner.wax_account, Decimal("25"))
            time.sleep(interval.req)
            return miner.buy_pack()
        except RequestException as e:
            miner.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            miner.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            miner.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except StopException as e:
            miner.log.exception("脚本错误: {0}".format(str(e)))
        except Exception as e:
            miner.log.exception("脚本错误: {0}".format(str(e)))
        return False



    def buy_packs(self):
        log.info("开始批量买包")
        self.batch_do(self.do_buy_pack)

    def batch_do(self, func):
        success_list = []
        error_list = []
        tasks: Dict[str, Future] = {}
        for item in self.sub_accounts:
            tasks[item.wax_account] = self.executor.submit(func, item)
        for k, v in tasks.items():
            if v.result():
                success_list.append(k)
            else:
                error_list.append(k)
        log.info(f"批量处理结束")
        log.info(f"执行成功{len(success_list)}个账户")
        log.info(f"执行失败{len(error_list)}个账户")
        log.info(f"成功列表: {success_list}")
        log.info(f"失败列表: {error_list}")


    def do_unpack(self, miner: Mining) -> bool:
        try:
            miner.log.info(f"开始使用账号【{miner.wax_account}】开包，归集卡")
            miner.check_signup()
            time.sleep(interval.req)
            miner.do_unpack()
            miner.log.info("准备归集卡片")
            return miner.transfer_all_yolasic(self.main_account.wax_account)
        except RequestException as e:
            miner.log.info("网络错误:{0}".format(str(e)))
        except NodeException as e:
            miner.log.info("节点错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except TransactionException as e:
            miner.log.info("交易错误,状态码 {0}, text: {1}".format(e.resp.status_code, e.resp.text))
        except StopException as e:
            miner.log.exception("脚本错误: {0}".format(str(e)))
        except Exception as e:
            miner.log.exception("脚本错误: {0}".format(str(e)))
        return False


    def unpacks(self):
        log.info("开始批量开包，归集卡")
        self.batch_do(self.do_unpack)




def main():
    parser = argparse.ArgumentParser(description="mining network")
    parser.add_argument("-config", default="user.yml", required=False)
    parser.add_argument("action", choices=["buy_packs", "unpacks"])
    #parser.add_argument("count", nargs="?", default= -1, type=int)
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf8") as file:
        data: CommentedMap = yaml.load(file)
        file.close()
    load_param(data)
    logger.init_loger(user_param.account)
    print("version: {0}".format(version))
    try:
        proxy = None
        if user_param.proxy:
            proxy = HttpProxy(user_param.proxy, user_param.proxy_username, user_param.proxy_password)

        batch = Batch()
        batch.main_account = Mining(user_param.account, user_param.private_key, proxy)
        batch.sub_accounts = []
        for item in user_param.sub_accounts:
            miner = Mining(item, user_param.sub_key, proxy)
            batch.sub_accounts.append(miner)
        log.info(f"一共{ len(batch.sub_accounts) }个子账户")
        if args.action == "buy_packs":
            batch.buy_packs()
        elif args.action == "unpacks":
            batch.unpacks()
    except Exception as e:
        log.exception("脚本出错:{0}".format(str(e)))



if __name__ == '__main__':
    main()
