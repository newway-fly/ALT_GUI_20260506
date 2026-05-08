# core/protocol.py
# -*- coding: utf-8 -*-
from enum import Enum, auto

class CmdType(Enum):
    # --- 基础/调试 ---
    CMD_RAW = auto()           # 透传
    
    # --- STM32 板级控制 ---
    STM_POWER_ON = auto()      # STM:power ALL ON
    STM_POWER_OFF = auto()     # STM:power ALL OFF
    STM_READ_POWER = auto()    # STM:ADC power (用于功耗计算)
    STM_READ_ALL_ADC = auto()  # STM:ADC ALL (读取所有ADC通道信息)
    
    STM_SET_DAC = auto()       # STM:DAC <ch> <val>
    STM_READ_DAC = auto()      # STM:DAC <ch> (读取DAC回读值)
    
    # --- 410 系统控制 ---
    SYS_IDLE = auto()          # 410:IDLE
    STOP_LOCK = auto()         # 410:STOP
    
    # --- 410 锁定模式 ---
    START_LOCK_UNIVERSAL = auto()  # 410:LOCKMODE_B
    START_LOCK_IQP = auto()        # 410:LOCK_A
    SET_LOCK_ENABLE = auto()       # 410:LOCK_EN
    
    # --- 410 硬件控制 ---
    DAC_WRITE = auto()         # 410:DAC
    ADC_READ_RAW = auto()      # 410:ADC
    READ_EXPD_CURR = auto()    # 410:ADC 77
    SET_EXPD_RES = auto()      # 410:EXPD
    
    # --- 410 扫描与微扰控制 (统一格式) ---
    START_SCAN = auto()        # 410:START_SCAN <MAX/NNQ>
    SET_DITHER = auto()        # 410:SET_DITHER <ch> <val>
    GET_DITHER = auto()        # 410:GET_DITHER <ch>

    GET_P22_DATA = auto()      # 410:GET_P22_DATA 1440
    GET_PD_ADC_NOISE = auto()   # 410:GET_PD_ADC_DATA
    EXPORT_NNQ_DATA = auto()   # 410:EXPORT_NNQ
    EXPORT_SCAN_CURVE = auto() # 410:GET_SCAN_CURVE <ch>




class Protocol:
    """协议层：指令打包与解析"""
    
    @staticmethod
    def pack(cmd_type: CmdType, *args) -> bytes:
        cmd_str = ""
        
        # === STM32 指令 ===
        if cmd_type == CmdType.STM_POWER_ON:
            cmd_str = "STM:power ALL ON"
        elif cmd_type == CmdType.STM_POWER_OFF:
            cmd_str = "STM:power ALL OFF"
        elif cmd_type == CmdType.STM_READ_POWER:
            cmd_str = "STM:ADC power"
        elif cmd_type == CmdType.STM_READ_ALL_ADC:
            cmd_str = "STM:ADC ALL"
        elif cmd_type == CmdType.STM_SET_DAC:
            cmd_str = f"STM:DAC {args[0]} {args[1]}"
        elif cmd_type == CmdType.STM_READ_DAC:
            cmd_str = f"STM:DAC {args[0]}"
            
        # === 410 指令 (自动加 410: 前缀) ===
        elif cmd_type == CmdType.DAC_WRITE:
            cmd_str = f"410:DAC {args[0]} {args[1]}"
        elif cmd_type == CmdType.ADC_READ_RAW:
            cmd_str = f"410:ADC {args[0]}"
        elif cmd_type == CmdType.READ_EXPD_CURR:
            cmd_str = "410:ADC 77"
        elif cmd_type == CmdType.STOP_LOCK:
            cmd_str = "410:STOP"
        elif cmd_type == CmdType.SYS_IDLE:
            cmd_str = "410:IDLE"
        elif cmd_type == CmdType.SET_LOCK_ENABLE:
            cmd_str = f"410:LOCK_EN {args[0]} {int(args[1])}"
        elif cmd_type == CmdType.SET_EXPD_RES:
            cmd_str = f"410:EXPD {args[0]}"
        elif cmd_type == CmdType.START_LOCK_UNIVERSAL:
            targets = "MAX MAX MAX MAX MAX MAX"
            if args and isinstance(args[0], (list, tuple)):
                targets = " ".join(args[0])
            cmd_str = f"410:LOCKMODE_B {targets}"
        elif cmd_type == CmdType.START_LOCK_IQP:
            cmd_str = "410:LOCK_A"
            
        # === 410 扫描与微扰指令 (全新重构) ===
        elif cmd_type == CmdType.START_SCAN:
            mode = args[0] if args else "MAX"
            cmd_str = f"410:START_SCAN {mode}"
        elif cmd_type == CmdType.SET_DITHER:
            cmd_str = f"410:SET_DITHER {args[0]} {args[1]}"
        elif cmd_type == CmdType.GET_DITHER:
            cmd_str = f"410:GET_DITHER {args[0]}"


        elif cmd_type == CmdType.GET_P22_DATA:
            cmd_str = f"410:GET_P22_DATA {args[0] if args else 1440}"
        elif cmd_type == CmdType.GET_PD_ADC_NOISE:
            cmd_str = "410:GET_PD_ADC_NOISE"
        elif cmd_type == CmdType.EXPORT_NNQ_DATA:
            cmd_str = "410:EXPORT_NNQ"
        elif cmd_type == CmdType.EXPORT_SCAN_CURVE:
            cmd_str = f"410:GET_SCAN_CURVE {args[0]}"

        # === 原始透传 ===
        elif cmd_type == CmdType.CMD_RAW:
            cmd_str = str(args[0])

        # 统一换行符
        cmd_str = cmd_str.rstrip() + "\r\n"
        return cmd_str.encode('ascii')

    @staticmethod
    def parse_line(line: str):
        line = line.strip()
        if not line: return None, None
            
        if line.startswith("STM:"):
            return "STM", line[4:].strip()
        elif line.startswith("410:"):
            return "410", line[4:].strip()
        else:
            return "RAW", line