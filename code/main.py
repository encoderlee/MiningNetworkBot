import logger
from logger import log
import ruamel.yaml
yaml = ruamel.yaml.YAML()
from ruamel.yaml.comments import CommentedMap
from settings import user_param, load_param
import argparse
from mining import HttpProxy, Mining, version


def main():
    parser = argparse.ArgumentParser(description="mining network")
    parser.add_argument("-config", default="user.yml", required=False)
    parser.add_argument("action", choices=["upgrade", "stake", "unstake", "getreward", "buy", "transfer", "sell",
                                           "buy_pack", "unpack", "speed_up", "test", "sh2btk", "btk2sh"])
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

        miner = Mining(user_param.account, user_param.private_key, proxy)

        if args.action == "upgrade":
            miner.do_upgrade()
        elif args.action == "getreward":
            miner.keep_getreward()
        elif args.action == "stake":
            miner.do_stake()
        elif args.action == "unstake":
            miner.do_unstake()
        elif args.action == "buy":
            miner.keep_buy()
        elif args.action == "transfer":
            miner.transfer()
        elif args.action == "sell":
            miner.do_sell()
        elif args.action == "buy_pack":
            miner.keep_buy_pack()
        elif args.action == "unpack":
            miner.do_unpack()
        elif args.action == "speed_up":
            miner.do_speed_up()
        elif args.action == "sh2btk":
            miner.keep_sh2btk()
        elif args.action == "btk2sh":
            miner.keep_btk2sh()
        elif args.action == "test":
            miner.test()
    except Exception as e:
        log.exception("脚本出错:{0}".format(str(e)))



if __name__ == '__main__':
    main()
