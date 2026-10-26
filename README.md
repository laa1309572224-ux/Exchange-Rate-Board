# Exchange Rate Board

MXN → 中间货币 → CNY 的公开汇率决策看板。

## 在线看板

部署完成后访问：

https://laa1309572224-ux.github.io/Exchange-Rate-Board/

## 功能

- 比较 USD、EUR、GBP、CAD、HKD、AUD、JPY、SGD 八条换汇路径
- 展示两段实时汇率与近 30 个工作日趋势
- 自动计算最终人民币和最优路径
- 手机、电脑响应式访问
- GitHub Actions 每天 08:00（墨西哥城时间）推送钉钉报告

## 仓库配置

在 `Settings → Secrets and variables → Actions` 中添加仓库 Secret：

- `DINGTALK_WEBHOOK`：钉钉机器人完整 Webhook 地址

Webhook 不应写入代码或提交到仓库。
