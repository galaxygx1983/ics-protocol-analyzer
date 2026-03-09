# BACnet 协议参考

## 协议概述

BACnet (Building Automation and Control Networks) 是楼宇自动化标准协议。

### 传输方式

| 传输方式 | 说明 | 端口/标识 |
|----------|------|----------|
| BACnet/IP | UDP传输 | 47808 (0xBAC0) |
| BACnet MS/TP | 串行通信 | RS-485 |
| BACnet Ethernet | 以太网 | 0x82BB |

## BACnet/IP 帧格式

```
┌─────────────────────────────────────────────────────────────────┐
│                        BVLC Header                              │
├──────────┬──────────┬──────────────────────────────────────────┤
│  版本    │  功能    │           长度/参数                       │
│  1 byte  │  1 byte  │           2 bytes                        │
├──────────┴──────────┴──────────────────────────────────────────┤
│                        NPDU                                     │
├─────────────────────────────────────────────────────────────────┤
│                        APDU                                     │
└─────────────────────────────────────────────────────────────────┘
```

## BVLC 功能码

| 功能码 | 名称 | 说明 |
|--------|------|------|
| 0x00 | BVLC-Result | 结果响应 |
| 0x01 | Write-Broadcast-Distribution-Table | 写广播表 |
| 0x02 | Read-Broadcast-Distribution-Table | 读广播表 |
| 0x03 | Read-Broadcast-Distribution-Table-Ack | 读广播表响应 |
| 0x04 | Foreign-Device-Registration | 外部设备注册 |
| 0x05 | Read-Foreign-Device-Table | 读外部设备表 |
| 0x06 | Read-Foreign-Device-Table-Ack | 读外部设备表响应 |
| 0x07 | Delete-Foreign-Device-Table-Entry | 删除外部设备表项 |
| 0x08 | Distribute-Broadcast-To-Network | 分发广播 |
| 0x09 | Original-Unicast-NPDU | 原始单播 |
| 0x0A | Original-Broadcast-NPDU | 原始广播 |

## NPDU 格式

```
┌──────────┬──────────┬──────────────────────────────────────────┐
│  版本    │  控制字节 │          地址信息（可选）                 │
│  1 byte  │  1 byte  │          可变长度                        │
├──────────┴──────────┴──────────────────────────────────────────┤
│                      Hop Count（可选）                          │
├─────────────────────────────────────────────────────────────────┤
│                   网络层消息（可选）                             │
└─────────────────────────────────────────────────────────────────┘
```

### 控制字节

```
┌────┬────┬────┬────┬────┬────┬────┬────┐
│ b7 │ b6 │ b5 │ b4 │ b3 │ b2 │ b1 │ b0 │
├────┼────┼────┼────┼────┼────┼────┼────┤
│NSDA│ NPM│ DADR预设│ SADR预设│B/C │保留│
└────┴────┴────┴────┴────┴────┴────┴────┘

- b7 (NSDA): 网络层消息目标地址存在
- b6 (NPM): 网络层协议消息
- b5 (DADR预设): 目标地址存在
- b3 (SADR预设): 源地址存在
- b1 (B/C): 广播/单播
```

## APDU 格式

### APDU 类型

| 类型 | 编码 | 说明 |
|------|------|------|
| Confirmed Request | 0 | 需确认请求 |
| Unconfirmed Request | 1 | 无确认请求 |
| Simple ACK | 2 | 简单确认 |
| Complex ACK | 3 | 复杂确认 |
| Segment ACK | 4 | 分段确认 |
| Error | 5 | 错误响应 |
| Reject | 6 | 拒绝 |
| Abort | 7 | 终止 |

### Confirmed Request APDU

```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│ PDU类型  │ Max Seg  │ Max Resp │ Invoke ID│ Service │
│ 4 bits   │ 4 bits   │ 4 bits   │  1 byte  │ Choice   │
├──────────┴──────────┴──────────┴──────────┴──────────┤
│                    Service Request                   │
└──────────────────────────────────────────────────────┘
```

### Unconfirmed Request APDU

```
┌──────────┬──────────┬──────────────────────────────────┐
│ PDU类型  │ Reserved │         Service Choice           │
│ 4 bits   │ 4 bits   │            1 byte                │
├──────────┴──────────┴──────────────────────────────────┤
│                    Service Request                     │
└────────────────────────────────────────────────────────┘
```

## 服务类型

### 确认服务

| 服务码 | 名称 | 说明 |
|--------|------|------|
| 0x00 | AcknowledgeAlarm | 确认报警 |
| 0x01 | ConfirmedCOVNotification | 确认COV通知 |
| 0x02 | ConfirmedEventNotification | 确认事件通知 |
| 0x04 | ReadProperty | 读属性 |
| 0x05 | ReadPropertyConditional | 条件读属性 |
| 0x06 | ReadPropertyMultiple | 读多属性 |
| 0x0F | WriteProperty | 写属性 |
| 0x10 | WritePropertyMultiple | 写多属性 |
| 0x11 | DeviceCommunicationControl | 设备通信控制 |
| 0x12 | ConfirmedPrivateTransfer | 确认私有传输 |
| 0x13 | ConfirmedTextMessage | 确认文本消息 |
| 0x14 | ReinitializeDevice | 重启设备 |
| 0x17 | AddListElement | 添加列表元素 |
| 0x18 | RemoveListElement | 删除列表元素 |

### 无确认服务

| 服务码 | 名称 | 说明 |
|--------|------|------|
| 0x00 | I-Am | 设备声明 |
| 0x01 | I-Have | 对象声明 |
| 0x02 | UnconfirmedCOVNotification | 无确认COV通知 |
| 0x03 | UnconfirmedEventNotification | 无确认事件通知 |
| 0x04 | UnconfirmedPrivateTransfer | 无确认私有传输 |
| 0x05 | UnconfirmedTextMessage | 无确认文本消息 |
| 0x06 | TimeSynchronization | 时间同步 |
| 0x07 | Who-Has | 谁拥有 |
| 0x08 | Who-Is | 谁是 |
| 0x09 | UTCTimeSynchronization | UTC时间同步 |

## 对象类型

| 类型码 | 名称 | 说明 |
|--------|------|------|
| 0 | Analog Input | 模拟输入 |
| 1 | Analog Output | 模拟输出 |
| 2 | Analog Value | 模拟值 |
| 3 | Binary Input | 二进制输入 |
| 4 | Binary Output | 二进制输出 |
| 5 | Binary Value | 二进制值 |
| 8 | Device | 设备 |
| 13 | Multi-state Input | 多状态输入 |
| 14 | Multi-state Output | 多状态输出 |
| 19 | Multi-state Value | 多状态值 |
| 20 | Trend Log | 趋势日志 |

## 属性标识符

| 属性ID | 名称 | 说明 |
|--------|------|------|
| 75 | Object Identifier | 对象标识符 |
| 77 | Object Name | 对象名称 |
| 79 | Object Type | 对象类型 |
| 85 | Present Value | 当前值 |
| 111 | Status Flags | 状态标志 |
| 121 | Device Address Binding | 设备地址绑定 |
| 28 | Description | 描述 |
| 17 | Units | 单位 |

## 解析示例

### Who-Is 请求

```
输入: 81 0B 00 0C 01 20 FF FF 00 FF 10 08

解析:
BVLC:
- 版本: 0x81
- 功能: 0x0B (Original-Broadcast-NPDU)
- 长度: 12

NPDU:
- 版本: 0x01
- 控制: 0x20 (广播)
- DNET: 0xFFFF (全网广播)

APDU:
- 类型: 0x10 (Unconfirmed Request)
- 服务: 0x08 (Who-Is)
```

### I-Am 响应

```
输入: 81 0A 00 15 01 00 00 10 00 C4 02 00 00 03 E8 21 22

解析:
BVLC:
- 版本: 0x81
- 功能: 0x0A (Original-Unicast-NPDU)
- 长度: 21

APDU:
- 类型: 0x10 (Unconfirmed Request)
- 服务: 0x00 (I-Am)
- 对象标识符: device,1000
- 最大APDU长度: 480
- 分段支持: 0x00
- 厂商ID: 0x03E8
```

### ReadProperty 请求

```
输入: 81 0A 00 14 01 00 C0 00 00 03 04 0C 00 00 00 55 19 55

解析:
BVLC:
- 版本: 0x81
- 功能: 0x0A (Original-Unicast-NPDU)
- 长度: 20

NPDU:
- 版本: 0x01
- 控制: 0x00

APDU:
- 类型: 0x00 (Confirmed Request, Max Seg=0, Max Resp=6)
- Invoke ID: 0x03
- 服务: 0x0C (ReadProperty)
- 对象标识符: analog-input,0
- 属性: 85 (Present Value)
```

### ReadProperty 响应

```
输入: 81 0A 00 12 01 00 C0 00 00 30 03 00 0C 00 00 00 55 19 55 3E 44 42 C8 00 00

解析:
APDU:
- 类型: 0x30 (Complex ACK)
- Invoke ID: 0x03
- 服务: 0x0C (ReadProperty)
- 对象标识符: analog-input,0
- 属性: 85 (Present Value)
- 值: 100.5 (REAL类型, 0x42C80000)
```

### WriteProperty 请求

```
输入: 81 0A 00 16 01 00 C0 00 00 05 0F 0C 02 00 00 01 55 3E 44 43 33 33 33

解析:
APDU:
- 类型: 0x05 (Confirmed Request)
- Invoke ID: 0x0F
- 服务: 0x0F (WriteProperty)
- 对象标识符: analog-output,1
- 属性: 85 (Present Value)
- 值: 179.2 (REAL类型)
- 优先级: 无优先级数组
```

## 编码规则

### 对象标识符编码

```
┌────────────────────┬────────────────────┐
│   对象类型(10bit)  │   实例号(22bit)    │
└────────────────────┴────────────────────┘

例: device,1000
- 类型: 8 (device) = 0b0000001000
- 实例: 1000 = 0x0003E8
- 编码: 0x020003E8
```

### 标签编码

```
┌──────────┬──────────┐
│ 标签号   │ 长度类型 │
│ 4 bits   │ 4 bits   │
└──────────┴──────────┘

长度类型:
- 0-4: 后续字节数
- 5: 后续1字节为长度
- 6: 后续2字节为长度
- 7: 后续4字节为长度
- F: 上下文标签/开放标签

例: 标签号=1, 长度=2
- 编码: 0x12 (标签号1, 长度类型2)
```

### REAL 类型编码

BACnet REAL 类型为 IEEE 754 单精度浮点数，大端格式。

```
值 100.5:
- 十六进制: 0x42C80000
- IEEE 754: sign=0, exp=133, mantissa=0x480000
```

## 常见问题

1. **设备发现失败**: 检查广播设置、BBMD配置
2. **读写超时**: 检查设备地址、Invoke ID匹配
3. **属性不支持**: 检查对象类型是否支持该属性
4. **权限错误**: 检查设备访问控制配置
5. **编码错误**: 检查标签编码、数据类型匹配