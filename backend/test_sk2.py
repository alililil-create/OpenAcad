import base64, binascii

SK = "WXpCaVptVm1aV1l3TnpNeE5EazRNamczTjJZNU1UUXhPRGxrT1dFMlpHWQ=="

decoded = base64.b64decode(SK)
text = decoded.decode('utf-8')

print(f"Base64 解码后: {text}")
print(f"长度: {len(text)}")

# 尝试 hex 解码
try:
    raw = bytes.fromhex(text)
    print(f"\nHex 解码后: {raw}")
    print(f"Hex 解码后(UTF-8): {raw.decode('utf-8')}")
except Exception as e:
    print(f"不是有效的hex: {e}")

# 直接用解码后的值作为 SK
print(f"\n{'='*60}")
print("尝试用 Base64 解码后的值作为 SK")
print(f"新SK: {text}")
