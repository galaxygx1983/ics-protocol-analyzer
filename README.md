# ICS Protocol Analyzer

> 工控协议通信报文解析与故障诊断工具

## 支持协议

- **Modbus**: TCP/RTU
- **IEC 60870-5**: IEC 101, IEC 104
- **IEC 61850**: GOOSE, SV, MMS
- **Siemens S7**: S7Comm, S7Plus
- **BACnet**: IP, MS/TP
- **MQTT**: 物联网协议

## 功能特性

- 解析工控协议报文的十六进制数据
- 分析通信日志排查故障
- 理解报文字段含义
- 诊断通信异常、超时、错误码
- 统计通信质量（响应时间、成功率等）

## 支持格式

| 输入 | 输出 |
|------|------|
| 十六进制字符串 | 结构化报告 |
| 带时间戳的日志文件 | JSON |
| PCAP 文件 | Markdown 表格 |

## 快速开始

```python
from ics_protocol_analyzer import ModbusParser

# 解析 Modbus TCP 报文
parser = ModbusParser()
result = parser.parse("00010000000601030000000a")
print(result.to_json())
```

## 详细文档

查看 [SKILL.md](SKILL.md) 获取完整使用指南。

## 许可证

MIT License