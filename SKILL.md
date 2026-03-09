---
name: ics-protocol-analyzer
description: |
  工控协议通信报文解析与故障诊断工具。支持Modbus TCP/RTU、IEC 101、IEC 104、IEC 61850、S7、BACnet等常见工控协议。

  TRIGGER 当用户需要：
  (1) 解析工控协议报文的十六进制数据
  (2) 分析通信日志排查故障
  (3) 理解报文字段含义
  (4) 诊断通信异常、超时、错误码
  (5) 统计通信质量（响应时间、成功率等）

  支持输入格式：十六进制字符串、带时间戳的日志文件
  支持输出格式：结构化报告、JSON、Markdown表格
---

# 工控协议报文分析

## 工作流程

```
1. 识别协议类型
     ↓
2. 解析报文结构
     ↓
3. 提取关键字段
     ↓
4. 故障诊断分析
     ↓
5. 生成报告
```

## 1. 协议识别

根据输入特征自动识别协议：

| 协议 | 识别特征 |
|------|----------|
| Modbus TCP | 端口502，事务ID+协议ID(0x0000)+长度 |
| Modbus RTU | 从站地址+功能码+数据+CRC16 |
| IEC 104 | 启动字节68H，APCI格式 |
| IEC 101 | 启动字节68H或10H，FT1.2帧格式 |
| IEC 61850 | MMS端口102，GOOSE以太网类型0x88B8 |
| S7 | TPKT + COTP + S7 PDU，端口102 |
| BACnet/IP | 端口47808(0xBAC0)，BVLC头部 |

**识别优先级**：先检查端口号和固定字节模式，再根据格式特征确认。

## 2. 解析流程

### 十六进制字符串输入

```
输入: "01 03 00 00 00 0A C4 0B"
处理:
  1. 去除空格和分隔符
  2. 转换为字节数组
  3. 识别协议类型
  4. 按协议格式解析各字段
  5. 验证校验码/CRC
```

### 日志文件输入

```
输入: 带时间戳的报文记录
处理:
  1. 提取时间戳
  2. 提取报文数据
  3. 解析每条报文
  4. 关联请求-响应对
  5. 计算响应时间
```

## 3. 协议解析参考

详细格式参考各协议文档：

- **Modbus**: [references/modbus.md](references/modbus.md)
- **IEC 104**: [references/iec104.md](references/iec104.md)
- **IEC 101**: [references/iec101.md](references/iec101.md)
- **IEC 61850**: [references/iec61850.md](references/iec61850.md)
- **S7**: [references/s7.md](references/s7.md)
- **BACnet**: [references/bacnet.md](references/bacnet.md)

## 4. 故障诊断

详见 [references/diagnosis.md](references/diagnosis.md)

### 诊断检查项

1. **格式验证**
   - 帧结构完整性
   - 校验码正确性
   - 字段值范围

2. **通信分析**
   - 请求-响应匹配
   - 响应时间统计
   - 超时检测

3. **异常检测**
   - 错误码识别
   - 异常序列号
   - 重传检测

## 5. 输出格式

### 结构化报告（默认）

```markdown
## 报文解析结果

**协议**: Modbus RTU
**方向**: 请求
**时间**: 2024-01-15 10:30:45.123

| 字段 | 十六进制 | 值 | 说明 |
|------|----------|-----|------|
| 从站地址 | 01 | 1 | 目标设备 |
| 功能码 | 03 | 03 | 读保持寄存器 |
| 起始地址 | 00 00 | 0 | 寄存器起始 |
| 数量 | 00 0A | 10 | 读取数量 |
| CRC | C4 0B | - | 校验通过 |

**诊断**: 正常报文
```

### JSON格式

```json
{
  "protocol": "modbus_rtu",
  "direction": "request",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "fields": {
    "slave_address": 1,
    "function_code": 3,
    "start_address": 0,
    "quantity": 10
  },
  "crc_valid": true,
  "diagnosis": "正常报文"
}
```

## 6. 使用示例

### 解析单个报文

```
用户: 解析这个Modbus报文：01 03 00 00 00 0A C4 0B

分析:
1. 识别为Modbus RTU格式
2. 解析各字段
3. 验证CRC
4. 输出结构化结果
```

### 分析日志文件

```
用户: 分析这段IEC 104通信日志，找出通信异常

处理:
1. 解析所有报文
2. 关联请求响应
3. 检查序列号连续性
4. 统计响应时间
5. 标记异常报文
6. 生成诊断报告
```

## 7. 解析脚本

使用 [scripts/parse_hex.py](scripts/parse_hex.py) 进行批量解析：

```bash
python parse_hex.py --protocol modbus --input hex_string
python parse_hex.py --protocol iec104 --file communication.log
```

## 8. 注意事项

1. **字节序**: 注意大小端，Modbus为大端，IEC为小端
2. **时间戳**: 日志分析时注意时区问题
3. **编码**: 十六进制输入不区分大小写
4. **截断**: 处理不完整报文时标注截断位置