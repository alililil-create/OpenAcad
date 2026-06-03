import base64

SK = "WXpCaVptVm1aV1l3TnpNeE5EazRNamczTjJZNU1UUXhPRGxrT1dFMlpHWQ=="

# 第一次 Base64 解码
decoded1 = base64.b64decode(SK)
text1 = decoded1.decode('utf-8')
print(f"第1次解码: {text1}")

# 第二次 Base64 解码
try:
    decoded2 = base64.b64decode(text1 + "==")
    text2 = decoded2.decode('utf-8')
    print(f"第2次解码: {text2}")
except Exception as e:
    print(f"第2次解码失败: {e}")

# 尝试直接用原始 SK
print("\n" + "="*60)
print("总结:")
print("  原始SK (Base64):", SK)
print("  解码后:", text1)
