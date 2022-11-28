# MiningNetworkBot
![version](https://img.shields.io/badge/version-2.7-blue)
![license](https://img.shields.io/badge/license-MIT-brightgreen)
![python_version](https://img.shields.io/badge/python-%3E%3D%203.6-brightgreen)
![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
[![](https://img.shields.io/badge/blog-@encoderlee-red)](https://encoderlee.blog.csdn.net)
#### 一个免费开源的MiningNetwork合约脚本，主要用于大户批量操作卡
![](https://raw.githubusercontent.com/encoderlee/MiningNetworkBot/main/doc/demo1.png)
注意，由于MiningNetwork游戏已经日落西山，本脚本已于2022年8月5日停止更新，对于一些新出的卡片和包不再支持，需要的可以自行修改代码

不过，买包和卖包功能，涉及到在原子市场上低价抢购和出售NFT，这部分代码可以参考借鉴，提取出来，用于开发NFT抢购和倒卖的脚本

## 说明
挖矿网络（Mining Network）官网： <https://miningnetwork.io>

之前我们推出过免费开源的农民世界（FarmersWorld）合约脚本:
<https://github.com/encoderlee/OpenFarmer>

外星世界（Alien Worlds）的合约脚本：
<https://github.com/encoderlee/OpenAlien>

老用户都懂，无需多言

欢迎关注我的博客：<https://encoderlee.blog.csdn.net>

### 欢迎加入我们的QQ群交流讨论：568229631

## 使用方法：

1.从源码运行，先安装 Python 环境，推荐安装 Python 3.9.13 版本，因为这是我们测试过的版本

下载地址：<https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe>

安装时记得勾选“Add Python 3.9 to PATH”

2.下载源码，在 github 项目页面上点击绿色按钮【Code】,【Download ZIP】,下载后解压出来

3.双击运行【install_dependencies.bat】安装依赖包，这个步骤每台电脑只需做一次

【注意】安装依赖包前请关闭梯子之类的代理，以免下载出错


4.先修改配置文件【user.yml】，再双击运行【bat】文件执行对应功能

## 功能

### 1.获取收益.bat
>python code\main.py getreward -config user.yml

批量采集已质押的卡获得的收益SH，虽然游戏本身有批量采集功能，但如果你的卡非常多，
超过2000张，手动在网页上操作，很容易出现采集不全的情况，脚本每500张为一组进行采集，
直到全部采集完。

而且脚本运行以后，24小时持续定时采集，默认每60分钟采集一次，采集后，可以自动兑换成BTK。

为什么要24小时持续采集，因为SH兑换BTK的汇率随时都在下跌，如果你每天甚至每两三天才手动采集一次，
肯定不如每小时采集后立马去兑换BTK划算。

影响参数：  
group：多少张卡为一组进行采集，默认500张  
getreward：采集间隔，默认60分钟  
withdraw：采集后是否立即换成BTK  

### 2.升级卡.bat
>python code\main.py upgrade -config user.yml

如果你有几千张0级卡，想批量升级到指定等级，运行该脚本功能是一个很好的选择。

影响参数：  
level：把卡升级到多少级  
rarity：只升级某种稀有度的卡  
max_count：最多升级多少张，0为全部升级

### 3.加速升级卡.bat
>python code\main.py speed_up -config user.yml

如果你有几千张已经进入升级状态，当你想批量加速升级，运行该脚本功能是一个很好的选择。

影响参数：  
rarity：只加速升级某种稀有度的卡  
max_count：最多加速升级多少张，0为全部加速升级。

### 4.质押.bat
>python code\main.py stake -config user.yml

批量质押卡

影响参数： 
level：只质押指定等级的卡，-1为全部质押
rarity：只质押某种稀有度的卡  
max_count：最多质押多少张，0为全部质押

### 5.解除质押.bat
>python code\main.py unstake -config user.yml

批量解除质押卡

影响参数：  
level：只解除质押指定等级的卡，-1为全部解除质押  
rarity：只解除质押某种稀有度的卡  
max_count：最多解除质押多少张，0为全部解除质押

### 6.买包.bat
>python code\main.py buy_pack -config user.yml

这个功能已经用不到了，以前每30分钟才能买一个包，所以需要脚本守着不停的买，现在买包没有限制了

影响参数：  
max_count：最多买多少个包，达到数量脚本停止，0为无限制，一直买

### 7.开包.bat
>python code\main.py unpack -config user.yml

批量开包

影响参数：  
max_count：最多开多少个包，达到数量脚本停止，0为无限制，全部开完

### 8.买卡.bat
>python code\main.py buy -config user.yml

从原子市场批量买卡，脚本不停的刷新，只要发现有价格低于设定的卡，就买下来。  
该功能的代码有很大参考意义，可以自行修改，用于在原子市场上抢购各种NFT，不止这款游戏

影响参数：  
max_count：最多买多少张卡，达到数量脚本停止，0为无限制，一直买  
rarity：只买指定稀有度的卡  
level：只买指定等级的卡，一般设置为-1，不管等级  
limit_price：卡的价格，低于该价格才买  
threads：买卡时并发线程数，用于加快抢购速度，比如突然刷出10张符合要求的卡，threads为1的话是一张一张的按顺序买
threads为10的话是10笔交易一起提交去买，尽量避免被别人抢先，但threads不是越大越好，太多线程，会被原子节点限制。

### 9.卖卡.bat
>python code\main.py sell -config user.yml

把卡批量上架到原子市场出售  
该功能的代码有很大参考意义，可以自行修改，用于在原子市场上倒卖各种NFT，赚取差价

影响参数：  
max_count：最多上架出售多少张卡，达到数量脚本停止，0为无限制，全部上架  
rarity：只上架指定稀有度的卡  
level：只上架指定等级的卡，一般设置为-1，不管等级  
sell_price：上架到原子市场的价格  

### 10.转移.bat
>python code\main.py transfer -config user.yml

将已经解除质押的卡批量转移到另一个账号

影响参数：  
level：只转移指定等级的卡，-1为全部转移  
rarity：只转移某种稀有度的卡  
max_count：最多转移多少张，0为全部转移  
to_account：要把卡转移到的目标账户  

### 11.SH兑换BTK.bat
>python code\main.py sh2btk -config user.yml

监视SH和BTK之间的汇率，达到要求就自动将SH兑换成BTK

影响参数：  
sh_price：10000SH等于多少btk，达到这个汇率，就将账户上的全部SH换成BTK  
interval_price： 检查汇率的扫描间隔，默认60秒  
record：在监视价格过程中（脚本运行过程中）是否把出现过的最高汇率和最低汇率记录到文件  


### 12.BTK兑换SH.bat
>python code\main.py btk2sh -config user.yml

监视SH和BTK之间的汇率，达到要求就自动将BTK兑换成SH

影响参数：  
sh_price：10000SH等于多少btk，达到这个汇率，就将账户上的全部BTK换成SH  
interval_price： 检查汇率的扫描间隔，默认60秒  
record：在监视价格过程中（脚本运行过程中）是否把出现过的最高汇率和最低汇率记录到文件  

### 13.小号批量买包.bat
>python code\batch.py buy_packs -config user.yml

现在这个功能没有用了，之前每个账号买包是有个数限制和间隔限制的，有再多BTK也没法一次性买很多包，
于是借助这个功能，准备若干个小号，脚本自动将BTK分发到每个小号上，然后自动控制这些小号分别去买包，每个小号各买一个包

影响参数：  
sub_key：小号的私钥，所有小号要求使用一样的私钥  
sub_accounts： 小号的账号名，这是一个数组，小号数量无限  


### 14.小号批量开包归集.bat
>python code\batch.py unpacks -config user.yml

现在这个功能没有用了，在执行完【小号批量买包.bat】后，再执行该功能，可以控制这些小号分别开包，然后把开得的卡片归集到主号上

影响参数：  
sub_key：小号的私钥，所有小号要求使用一样的私钥  
sub_accounts： 小号的账号名，这是一个数组，小号数量无限 

## 配置文件说明

```yaml
#注意，每个参数名的冒号后面，都有一个空格，修改参数不要丢了空格

# wax节点地址，使用公共节点，有时候会网络不通，或者访问太频繁被限制，出现429错误，可以换节点，或者搭建私有节点
# 公共节点列表：https://wax.eosio.online/endpoints

rpc_domain: https://wax.pink.gg


# 原子节点
rpc_atomic: https://aa.dapplica.io
# http代理（比如127.0.0.1:10808)
# 给脚本设置HTTP代理，这样可以在一定程度上解决公共节点限制访问的问题，不需要则留空
proxy:
proxy_username:
proxy_password:

# cpu代付号,cpu_key填写该代付号私钥，不需要代付则留空
cpu_account:
cpu_key:

# WAX主账号
account: fuckpayforit
private_key: 5J94Yqxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# WAX子账号
# 子账号私钥
sub_key: 5J94Yqxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 子账号名
sub_accounts:
  - zhuandafao12
  - zhuandafao13


# 功能：【获取收益】【升级卡】【加速升级卡】【质押】【解除质押】【开包】【买包】【批量买包】【批量开包归集】【转移】【买卡】【卖卡】

# 通用参数

# 要处理的卡类型 free、common、rare、epic、legendary
# 受此参数影响的功能：【升级卡】【加速升级卡】【质押】【解除质押】【转移】【买卡】【卖卡】
# 收集奖励不受此参数影响，收集奖励总是收集全部卡的奖励
rarity: free
card_class: 0

# max_count 最多质押多少个，最多解除质押多少个，最多升级多少个，最多加速升级多少个，最多买多少个，最多转多少个，最多卖多少个， 最多买多少个包
# 0就是无限制，一直买，全部质押，全部解除质押，全部升级，全部转走，全部卖掉...
# 受此参数影响的功能：【升级卡】【加速升级卡】【质押】【解除质押】【转移】【买卡】【卖卡】【买包】【开包】
max_count: 0

# 要处理的卡的等级
# 设置为0，只买0级卡，设置为100，只买100级卡，设置为-1，则不管等级，全部都处理
#但一般买卡的话，如果不管等级，一般设置为-1，反正买卡是低价优先，设置为-1的话，有时候可以低价买到大于0级的卡
# 受此参数影响的功能：【升级卡】【质押】【解除质押】【转移】【买卡】【卖卡】
# 升级卡时，该参数的含义为升到多少级s
level: -1


# getreward 收集卡奖励
# 收集奖励间隔（分钟）
getreward: 60
# 收集奖励后是否立即换成BTK
withdraw: true
# 一笔交易收集500张卡的奖励,即每500张每500张的收集
group: 500


# buy 原子市场扫灰卡
# 加速购买，同时多少个请求
threads: 5
# 扫货限制价格
limit_price: "1.1"


# transfer 批量转移灰卡到别的账户
#要转移的目标账户
to_account: "xxxxxxxxxxxxxxxxxxxx"

# sell 批量上架到原子市场卖卡
# 上架到原子市场的价格
sell_price: "5000"


# sh与btk兑换价格，达到后进行兑换
# 10000SH等于多少btk
sh_price: 0.0006

# 扫描价格间隔(秒)
interval_price: 60

# 是否记录最高最低价到文件
record: true

```

## 常用工具

【nodepad++】[https://notepad-plus-plus.org/downloads/v8.4.2](https://notepad-plus-plus.org/downloads/v8.4.2)

文本编辑器，编辑修改【user.yml】配置文件更愉快

【cmder】[https://cmder.net](https://cmder.net)

替代 windows 自带的 cmd 命令行工具，防止脚本假死

系统自带的 cmd 命令行工具，默认开启快速编辑模式，有时候因为鼠标键盘意外操作，

日志会留在一个地方，处于假死状态，导致脚本不能持续运行，换用【cmder】解决该问题

## 常见错误
1.交易错误

交易错误的原因有很多种，比如智能合约报错，CPU不足，秘钥不对，WAX节点限制等

连续出现5次交易出错，脚本将停止，此时需要手工检查问题或更换节点

为什么不一直继续反复重试？因为反复提交错误的交易，公共节点就会把你拉黑，需要24小时之后才能使用该节点了

自行架设 WAX 私有节点，会在一定程度上改善此问题

2.节点错误

节点错误，尤其是 429 错误，主要是因为你一个IP下面同时跑的号太多了，请求频繁，被节点拉黑

公共节点毕竟是面向全球的免费服务，为了防止滥用，做了很多限制

每N个号设置一个代理IP，或者自行架设 WAX 私有节点，会在一定程度上改善此问题

## 欢迎打赏

wax钱包地址：

m45yy.wam

## 更新记录
v2.1  
2022年6月13日

新增功能
【小号批量买包.bat】
【小号批量开包归集.bat】

这个功能意思是你有很多BTK，想买很多包来开，但是一个账号每30分钟只能买一个包，
那么就可以在配置文件的sub_accounts参数中填写你的N个小号，假如有10个小号，
那么运行【小号批量买包.bat】，会自动从主账号上给每个小号转25BTK，然后这些小号分别买包，
这个时候，10个小号上就有10个包了，接下来运行【小号批量开包归集.bat】，这10个小号就会分别开包，
然后把开出来的卡转回主号

该功能主要是大户使用，一般玩家使用【买包.bat】就行了，脚本每30分钟定时去买包
如果包太多，开的麻烦，可以使用【开包.bat】功能，自动的一个个把你的包全部开完

v2.4  
2022年6月16日

新增参数：  
rarity: free  
这里可以设置要处理的卡类型，以前只能处理灰卡free，现在各种颜色的卡都可以处理了  
可选值：free、common、rare、epic、legendary  
受此参数影响的功能：【升级卡】【加速升级卡】【质押】【解除质押】【转移】【买卡】【卖卡】  
比如设置为  
rarity: common  
那么，【买卡】的时候只买绿卡  

新增功能：  
【加速升级卡.bat】  
需要先运行【升级卡.bat】，等卡已经进入升级状态后，再运行【加速升级卡.bat】，消耗sh加速升级  

修改功能：  
【升级卡.bat】  
以前只能把灰卡升级到100级，现在绿卡、蓝卡等各种卡，都可以升级，想升到多少级你说了算

比如:  
rarity: common  
level: 122  
max_count: 1  
就是把1张绿卡升级到122级  

max_count: 0  
的话就是把所有可以升级的绿卡都升级到122级


V2.5.0  
2022年6月22日

新增参数：  
withdraw: true  
收集奖励后是否立即换成BTK  
true为是，false为否  

支持最新的50BTK的包，买包和开包

V2.6.1  
2022年7月1日

新增功能：  
【SH兑换BTK】  
【BTK兑换SH】  

新增参数：  
\# sh和btk之间兑换价格，达到后进行兑换  
\# 1btk等于多少sh  
btk_price: 13300000

\# 扫描价格间隔(秒)  
interval_price: 60

v2.7
2022年8月4日

支持class4的卡
