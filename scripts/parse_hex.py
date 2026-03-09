#!/usr/bin/env python3
"""
工控协议报文解析工具
支持: Modbus RTU/TCP, IEC 101/104, IEC 61850, S7, BACnet

用法:
    python parse_hex.py --protocol modbus --input "01 03 00 00 00 0A C4 0B"
    python parse_hex.py --protocol iec104 --file communication.log
    python parse_hex.py --auto "68 04 07 00 00 00"
"""

import argparse
import re
import sys
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
import json


class Protocol(Enum):
    MODBUS_RTU = "modbus_rtu"
    MODBUS_TCP = "modbus_tcp"
    IEC104 = "iec104"
    IEC101 = "iec101"
    IEC61850 = "iec61850"
    S7 = "s7"
    BACNET = "bacnet"
    AUTO = "auto"


@dataclass
class ParseResult:
    protocol: str
    direction: str  # request/response
    fields: Dict[str, Any]
    raw_hex: str
    valid: bool
    diagnosis: str
    error: Optional[str] = None


def hex_to_bytes(hex_str: str) -> bytes:
    """将十六进制字符串转换为字节"""
    hex_str = re.sub(r'[\s\-:,]', '', hex_str)
    return bytes.fromhex(hex_str)


def bytes_to_hex(data: bytes) -> str:
    """将字节转换为十六进制字符串"""
    return ' '.join(f'{b:02X}' for b in data)


def crc16_modbus(data: bytes) -> int:
    """计算Modbus CRC-16"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def detect_protocol(data: bytes) -> Optional[Protocol]:
    """自动检测协议类型"""
    if len(data) < 2:
        return None

    # IEC 104/101: 以68H开头
    if data[0] == 0x68:
        if len(data) >= 6:
            length = data[1]
            # IEC 104 特征: 长度合理，后续有APCI
            if length <= 253 and len(data) >= 6:
                # 检查是否是U帧或I帧
                control = data[2]
                if control in [0x07, 0x0B, 0x13, 0x23, 0x43, 0x83]:  # U帧
                    return Protocol.IEC104
                elif (control & 0x01) == 0:  # I帧
                    return Protocol.IEC104
                elif (control & 0x03) == 0x01:  # S帧
                    return Protocol.IEC104
        return Protocol.IEC101

    # IEC 101 固定帧: 以10H开头，以16H结尾
    if data[0] == 0x10 and data[-1] == 0x16:
        return Protocol.IEC101

    # TPKT (S7/IEC61850): 以03H开头
    if data[0] == 0x03 and len(data) >= 4:
        length = (data[2] << 8) | data[3]
        if length == len(data):
            if len(data) > 7 and data[5] == 0xF0:  # COTP
                if len(data) > 8 and data[8] == 0x32:  # S7 PDU
                    return Protocol.S7
                else:
                    return Protocol.IEC61850

    # BACnet/IP: 以81H开头，端口47808
    if data[0] == 0x81 and len(data) >= 4:
        if data[1] in range(0x00, 0x0B):  # BVLC function
            return Protocol.BACNET

    # Modbus TCP: 检查长度字段和协议ID
    if len(data) >= 8:
        protocol_id = (data[2] << 8) | data[3]
        length = (data[4] << 8) | data[5]
        if protocol_id == 0x0000 and length > 0:
            return Protocol.MODBUS_TCP

    # Modbus RTU: 检查功能码和CRC
    if len(data) >= 4:
        if data[1] in [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x0F, 0x10]:
            # 验证CRC
            calculated = crc16_modbus(data[:-2])
            received = data[-2] | (data[-1] << 8)
            if calculated == received:
                return Protocol.MODBUS_RTU

    return None


class ModbusParser:
    """Modbus协议解析器"""

    FUNCTION_CODES = {
        0x01: "读线圈",
        0x02: "读离散输入",
        0x03: "读保持寄存器",
        0x04: "读输入寄存器",
        0x05: "写单个线圈",
        0x06: "写单个寄存器",
        0x0F: "写多个线圈",
        0x10: "写多个寄存器",
    }

    EXCEPTION_CODES = {
        0x01: "非法功能码",
        0x02: "非法数据地址",
        0x03: "非法数据值",
        0x04: "从站设备故障",
    }

    @classmethod
    def parse_rtu(cls, data: bytes) -> ParseResult:
        """解析Modbus RTU报文"""
        if len(data) < 4:
            return ParseResult(
                protocol="modbus_rtu",
                direction="unknown",
                fields={},
                raw_hex=bytes_to_hex(data),
                valid=False,
                diagnosis="报文长度不足",
                error="长度错误"
            )

        slave_addr = data[0]
        func_code = data[1]
        is_exception = func_code & 0x80

        fields = {
            "从站地址": slave_addr,
            "功能码": func_code if not is_exception else func_code & 0x7F,
        }

        if is_exception:
            exception_code = data[2]
            fields["异常码"] = exception_code
            fields["异常说明"] = cls.EXCEPTION_CODES.get(exception_code, "未知异常")
            diagnosis = f"异常响应: {fields['异常说明']}"
        else:
            func_name = cls.FUNCTION_CODES.get(func_code, f"未知功能码(0x{func_code:02X})")
            fields["功能名称"] = func_name

            if func_code in [0x01, 0x02, 0x03, 0x04]:  # 读请求
                if len(data) >= 6:
                    start_addr = (data[2] << 8) | data[3]
                    quantity = (data[4] << 8) | data[5]
                    fields["起始地址"] = start_addr
                    fields["数量"] = quantity
                    diagnosis = f"读请求: {func_name}, 起始地址{start_addr}, 数量{quantity}"
                else:
                    diagnosis = "读请求，数据不完整"

            elif func_code in [0x05]:  # 写单个线圈
                if len(data) >= 6:
                    addr = (data[2] << 8) | data[3]
                    value = "ON" if data[4] == 0xFF else "OFF"
                    fields["地址"] = addr
                    fields["值"] = value
                    diagnosis = f"写单个线圈: 地址{addr}, 值{value}"

            elif func_code in [0x06]:  # 写单个寄存器
                if len(data) >= 6:
                    addr = (data[2] << 8) | data[3]
                    value = (data[4] << 8) | data[5]
                    fields["地址"] = addr
                    fields["值"] = value
                    diagnosis = f"写单个寄存器: 地址{addr}, 值{value}"

            elif func_code in [0x0F, 0x10]:  # 写多个
                if len(data) >= 7:
                    start_addr = (data[2] << 8) | data[3]
                    quantity = (data[4] << 8) | data[5]
                    byte_count = data[6]
                    fields["起始地址"] = start_addr
                    fields["数量"] = quantity
                    fields["字节数"] = byte_count
                    diagnosis = f"写多个: 起始地址{start_addr}, 数量{quantity}"

            # 响应处理
            elif func_code in [0x01, 0x02] and len(data) > 3:  # 读线圈/离散输入响应
                byte_count = data[2]
                fields["字节数"] = byte_count
                diagnosis = f"读响应: {byte_count}字节数据"

            elif func_code in [0x03, 0x04] and len(data) > 3:  # 读寄存器响应
                byte_count = data[2]
                fields["字节数"] = byte_count
                reg_values = []
                for i in range(3, 3 + byte_count, 2):
                    if i + 1 < len(data):
                        val = (data[i] << 8) | data[i+1]
                        reg_values.append(val)
                fields["寄存器值"] = reg_values
                diagnosis = f"读响应: {len(reg_values)}个寄存器"

        # 验证CRC
        calculated_crc = crc16_modbus(data[:-2])
        received_crc = data[-2] | (data[-1] << 8)
        fields["CRC"] = f"{received_crc:04X}"
        crc_valid = calculated_crc == received_crc
        fields["CRC验证"] = "通过" if crc_valid else "失败"

        if not crc_valid:
            diagnosis += " [CRC错误]"

        return ParseResult(
            protocol="modbus_rtu",
            direction="exception" if is_exception else ("request" if len(data) <= 8 else "response"),
            fields=fields,
            raw_hex=bytes_to_hex(data),
            valid=crc_valid,
            diagnosis=diagnosis
        )


class IEC104Parser:
    """IEC 104协议解析器"""

    U_FRAME_TYPES = {
        0x07: "STARTDT act (启动数据传输激活)",
        0x0B: "STARTDT con (启动数据传输确认)",
        0x13: "STOPDT act (停止数据传输激活)",
        0x23: "STOPDT con (停止数据传输确认)",
        0x43: "TESTFR act (测试帧激活)",
        0x83: "TESTFR con (测试帧确认)",
    }

    TYPE_IDS = {
        1: "M_SP_NA_1 (单点信息)",
        3: "M_DP_NA_1 (双点信息)",
        9: "M_ME_NA_1 (测量值-标度化值)",
        11: "M_ME_NB_1 (测量值-浮点数)",
        13: "M_ME_NC_1 (测量值-IEEE浮点)",
        30: "M_SP_TB_1 (带时标单点信息)",
        35: "M_ME_TF_1 (带时标测量值-浮点)",
        45: "C_SC_NA_1 (单点命令)",
        100: "C_IC_NA_1 (总召唤命令)",
    }

    COTS = {
        1: "周期/循环",
        3: "突发",
        5: "请求",
        6: "激活",
        7: "激活确认",
        20: "响应站召唤",
        44: "未知的类型标识",
        45: "未知的传输原因",
        46: "未知的应用服务数据单元公共地址",
    }

    @classmethod
    def parse(cls, data: bytes) -> ParseResult:
        """解析IEC 104报文"""
        if len(data) < 6:
            return ParseResult(
                protocol="iec104",
                direction="unknown",
                fields={},
                raw_hex=bytes_to_hex(data),
                valid=False,
                diagnosis="报文长度不足",
                error="长度错误"
            )

        if data[0] != 0x68:
            return ParseResult(
                protocol="iec104",
                direction="unknown",
                fields={},
                raw_hex=bytes_to_hex(data),
                valid=False,
                diagnosis="启动字节错误",
                error="格式错误"
            )

        length = data[1]
        fields = {
            "启动字节": "68H",
            "APCI长度": length,
        }

        # 解析控制域
        control = data[2:6]
        frame_type = control[0] & 0x03

        if frame_type == 0:  # I帧
            send_seq = ((control[0] >> 1) | (control[1] << 7)) & 0x7FFF
            recv_seq = ((control[2] >> 1) | (control[3] << 7)) & 0x7FFF
            fields["帧类型"] = "I帧 (信息传输)"
            fields["发送序列号"] = send_seq
            fields["接收序列号"] = recv_seq
            direction = "data"

            # 解析ASDU (如果有)
            if len(data) > 6:
                asdu = data[6:]
                if len(asdu) >= 6:
                    type_id = asdu[0]
                    vsq = asdu[1]
                    cot = asdu[2] | (asdu[3] << 8) if len(asdu) > 3 else asdu[2]
                    common_addr = asdu[4] | (asdu[5] << 8) if len(asdu) > 5 else asdu[4]

                    fields["类型标识"] = f"{type_id} ({cls.TYPE_IDS.get(type_id, '未知')})"
                    fields["可变结构限定词"] = vsq
                    fields["传输原因"] = f"{cot} ({cls.COTS.get(cot, '未知')})"
                    fields["公共地址"] = common_addr

            diagnosis = f"I帧: 发送序号={send_seq}, 接收序号={recv_seq}"

        elif frame_type == 1:  # S帧
            recv_seq = ((control[2] >> 1) | (control[3] << 7)) & 0x7FFF
            fields["帧类型"] = "S帧 (确认帧)"
            fields["接收序列号"] = recv_seq
            direction = "ack"
            diagnosis = f"S帧: 确认序号={recv_seq}"

        else:  # U帧
            u_type = control[0]
            fields["帧类型"] = "U帧 (无编号控制帧)"
            fields["U帧类型"] = cls.U_FRAME_TYPES.get(u_type, f"未知(0x{u_type:02X})")
            direction = "control"
            diagnosis = cls.U_FRAME_TYPES.get(u_type, "未知U帧")

        return ParseResult(
            protocol="iec104",
            direction=direction,
            fields=fields,
            raw_hex=bytes_to_hex(data),
            valid=True,
            diagnosis=diagnosis
        )


class S7Parser:
    """S7协议解析器"""

    AREA_CODES = {
        0x81: "I (输入)",
        0x82: "Q (输出)",
        0x83: "M (中间存储器)",
        0x84: "DB (数据块)",
        0x85: "DI (背景数据块)",
        0x86: "C (计数器)",
        0x87: "T (定时器)",
    }

    TYPE_CODES = {
        0x01: "BIT",
        0x02: "BYTE",
        0x03: "CHAR",
        0x04: "WORD",
        0x05: "INT",
        0x06: "DWORD",
        0x07: "DINT",
        0x08: "REAL",
    }

    ROSCTR_TYPES = {
        0x01: "JOB (作业请求)",
        0x02: "ACK (确认响应)",
        0x03: "ACK_DATA (数据响应)",
        0x07: "USER_DATA (用户数据)",
    }

    @classmethod
    def parse(cls, data: bytes) -> ParseResult:
        """解析S7报文"""
        if len(data) < 16:
            return ParseResult(
                protocol="s7",
                direction="unknown",
                fields={},
                raw_hex=bytes_to_hex(data),
                valid=False,
                diagnosis="报文长度不足",
                error="长度错误"
            )

        # TPKT
        tpkt_version = data[0]
        tpkt_length = (data[2] << 8) | data[3]
        fields = {
            "TPKT版本": tpkt_version,
            "TPKT长度": tpkt_length,
        }

        # COTP
        cotp_length = data[4]
        cotp_type = data[5]
        fields["COTP长度"] = cotp_length
        fields["COTP类型"] = f"0x{cotp_type:02X}"

        # S7 PDU (如果是数据帧)
        if cotp_type == 0xF0 and len(data) > 8:
            s7_start = 7 if cotp_length == 2 else 8
            if len(data) > s7_start + 8:
                protocol = data[s7_start]
                rosctr = data[s7_start + 1]
                pdu_ref = (data[s7_start + 4] << 8) | data[s7_start + 5]
                param_len = (data[s7_start + 6] << 8) | data[s7_start + 7]

                fields["S7协议标识"] = f"0x{protocol:02X}"
                fields["ROSCTR"] = cls.ROSCTR_TYPES.get(rosctr, f"未知(0x{rosctr:02X})")
                fields["PDU引用"] = pdu_ref
                fields["参数长度"] = param_len

                diagnosis = f"S7 {cls.ROSCTR_TYPES.get(rosctr, '未知类型')}, PDU引用={pdu_ref}"
            else:
                diagnosis = "S7 COTP连接帧"
        else:
            diagnosis = f"COTP帧, 类型=0x{cotp_type:02X}"

        return ParseResult(
            protocol="s7",
            direction="request" if fields.get("ROSCTR", "").startswith("JOB") else "response",
            fields=fields,
            raw_hex=bytes_to_hex(data),
            valid=True,
            diagnosis=diagnosis
        )


class BACnetParser:
    """BACnet/IP协议解析器"""

    BVLC_FUNCTIONS = {
        0x00: "BVLC-Result",
        0x04: "Foreign-Device-Registration",
        0x09: "Original-Unicast-NPDU",
        0x0A: "Original-Broadcast-NPDU",
        0x0B: "Distribute-Broadcast-To-Network",
    }

    SERVICE_CODES = {
        0x04: "ReadProperty",
        0x05: "ReadPropertyConditional",
        0x06: "ReadPropertyMultiple",
        0x0F: "WriteProperty",
        0x10: "WritePropertyMultiple",
    }

    UNCONFIRMED_SERVICES = {
        0x00: "I-Am",
        0x01: "I-Have",
        0x07: "Who-Has",
        0x08: "Who-Is",
    }

    @classmethod
    def parse(cls, data: bytes) -> ParseResult:
        """解析BACnet/IP报文"""
        if len(data) < 4:
            return ParseResult(
                protocol="bacnet",
                direction="unknown",
                fields={},
                raw_hex=bytes_to_hex(data),
                valid=False,
                diagnosis="报文长度不足",
                error="长度错误"
            )

        # BVLC
        bvlc_version = data[0]
        bvlc_function = data[1]
        bvlc_length = (data[2] << 8) | data[3]

        fields = {
            "BVLC版本": bvlc_version,
            "BVLC功能": cls.BVLC_FUNCTIONS.get(bvlc_function, f"未知(0x{bvlc_function:02X})"),
            "BVLC长度": bvlc_length,
        }

        # NPDU
        if len(data) > 5:
            npdu_version = data[4]
            npdu_control = data[5]
            fields["NPDU版本"] = npdu_version
            fields["NPDU控制"] = f"0x{npdu_control:02X}"

        # APDU
        if len(data) > 7:
            apdu_type = (data[6] >> 4) & 0x0F
            if apdu_type == 0:  # Confirmed Request
                invoke_id = data[8] if len(data) > 8 else 0
                service = data[9] if len(data) > 9 else 0
                fields["APDU类型"] = "Confirmed Request"
                fields["调用ID"] = invoke_id
                fields["服务"] = cls.SERVICE_CODES.get(service, f"未知(0x{service:02X})")
            elif apdu_type == 1:  # Unconfirmed Request
                service = data[7] if len(data) > 7 else 0
                fields["APDU类型"] = "Unconfirmed Request"
                fields["服务"] = cls.UNCONFIRMED_SERVICES.get(service, f"未知(0x{service:02X})")
            elif apdu_type == 2:  # Simple ACK
                fields["APDU类型"] = "Simple ACK"
            elif apdu_type == 3:  # Complex ACK
                fields["APDU类型"] = "Complex ACK"

        diagnosis = f"BACnet/IP: {fields.get('BVLC功能', '未知')}"
        if '服务' in fields:
            diagnosis += f", 服务={fields['服务']}"

        return ParseResult(
            protocol="bacnet",
            direction="request" if "Request" in fields.get("APDU类型", "") else "response",
            fields=fields,
            raw_hex=bytes_to_hex(data),
            valid=True,
            diagnosis=diagnosis
        )


def parse_hex(hex_str: str, protocol: Protocol = Protocol.AUTO) -> ParseResult:
    """解析十六进制报文"""
    data = hex_to_bytes(hex_str)

    if protocol == Protocol.AUTO:
        protocol = detect_protocol(data)
        if protocol is None:
            return ParseResult(
                protocol="unknown",
                direction="unknown",
                fields={},
                raw_hex=bytes_to_hex(data),
                valid=False,
                diagnosis="无法识别协议类型",
                error="协议识别失败"
            )

    parsers = {
        Protocol.MODBUS_RTU: ModbusParser.parse_rtu,
        Protocol.IEC104: IEC104Parser.parse,
        Protocol.S7: S7Parser.parse,
        Protocol.BACNET: BACnetParser.parse,
    }

    parser = parsers.get(protocol)
    if parser:
        return parser(data)
    else:
        return ParseResult(
            protocol=protocol.value,
            direction="unknown",
            fields={},
            raw_hex=bytes_to_hex(data),
            valid=False,
            diagnosis=f"暂不支持 {protocol.value} 协议解析",
            error="不支持"
        )


def format_output(result: ParseResult, format_type: str = "markdown") -> str:
    """格式化输出结果"""
    # 设置UTF-8编码输出
    import sys
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    if format_type == "json":
        return json.dumps({
            "protocol": result.protocol,
            "direction": result.direction,
            "fields": result.fields,
            "raw_hex": result.raw_hex,
            "valid": result.valid,
            "diagnosis": result.diagnosis,
            "error": result.error
        }, ensure_ascii=False, indent=2)

    elif format_type == "markdown":
        lines = [
            "## 报文解析结果",
            "",
            f"**协议**: {result.protocol}",
            f"**方向**: {result.direction}",
            f"**有效性**: {'通过' if result.valid else '失败'}",
            "",
            "| 字段 | 值 |",
            "|------|-----|",
        ]
        for key, value in result.fields.items():
            lines.append(f"| {key} | {value} |")
        lines.extend([
            "",
            f"**原始报文**: `{result.raw_hex}`",
            f"**诊断**: {result.diagnosis}",
        ])
        if result.error:
            lines.append(f"**错误**: {result.error}")
        return "\n".join(lines)

    else:  # simple text
        lines = [
            f"协议: {result.protocol}",
            f"方向: {result.direction}",
            f"有效: {result.valid}",
            "字段:",
        ]
        for key, value in result.fields.items():
            lines.append(f"  {key}: {value}")
        lines.append(f"诊断: {result.diagnosis}")
        if result.error:
            lines.append(f"错误: {result.error}")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="工控协议报文解析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --protocol modbus --input "01 03 00 00 00 0A C4 0B"
  %(prog)s --protocol iec104 --input "68 04 07 00 00 00"
  %(prog)s --auto --input "68 04 07 00 00 00"
  %(prog)s --protocol modbus --input "01 03 00 00 00 0A C4 0B" --format json
        """
    )
    parser.add_argument("--protocol", choices=[p.value for p in Protocol],
                        default="auto", help="协议类型")
    parser.add_argument("--input", help="十六进制报文字符串")
    parser.add_argument("--file", help="日志文件路径")
    parser.add_argument("--format", choices=["markdown", "json", "text"],
                        default="markdown", help="输出格式")
    parser.add_argument("--auto", action="store_true", help="自动检测协议")

    args = parser.parse_args()

    if not args.input and not args.file:
        parser.print_help()
        sys.exit(1)

    protocol = Protocol.AUTO if args.auto else Protocol(args.protocol)

    if args.input:
        result = parse_hex(args.input, protocol)
        print(format_output(result, args.format))

    if args.file:
        print(f"文件解析功能待实现: {args.file}")


if __name__ == "__main__":
    main()