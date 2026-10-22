import re

def smart_split_versions(value: str):
    """拆分版本/配色枚举，但保护括号（包括全角/半角）内部的分隔符。"""
    # 如果没有分隔符，直接返回
    if not any(sep in value for sep in "、，,/") and "/" not in value:
        return [value]
    
    # 状态机扫描，在括号深度为0时才按分隔符拆分
    # 优先顿号/逗号，次选斜杠
    has_comma = any(sep in value for sep in "、，,")
    seps = set("、，,") if has_comma else set("/")
    
    parts = []
    current = []
    depth = 0
    
    for ch in value:
        if ch in "（(":
            depth += 1
            current.append(ch)
        elif ch in "）)":
            if depth > 0:
                depth -= 1
            current.append(ch)
        elif depth == 0 and ch in seps:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(ch)
            
    part = "".join(current).strip()
    if part:
        parts.append(part)
        
    return parts or [value]

test_cases = [
    "原色、修复版神圣完美独角兽",
    "原色、七幺幺限定觉醒绿、最终决战样式蓝色、黄金双子星（香槟金、土豪金）、再生环保配色荧光绿",
    "涂装版（爆桑女妖、菲尼克斯天线及大盾、透明骨架、结晶板件）",
    "原色、结晶蓝色、结晶暗紫色、结晶透明（涂装独角兽2.0）",
    "红谷版本（带光束战斧、三段支架）、最终决战样式绿谷版本",
    "原色、黑金配色（成型色）、板喷消光黑、绿骨、会场限定彩透版",
    "原色、彩透版（低饱和带闪粉）、实色版（美团配色）、电镀银、电镀紫、电镀黑、电镀暗钢、电镀黑紫",
    "原色电镀金、电镀红、电镀绿、电镀紫、电镀暗钢、电镀粉、电镀银（2C型包装）",
]

for tc in test_cases:
    print("INPUT :", tc)
    res = smart_split_versions(tc)
    print("OUTPUT:", res)
    print("-" * 50)
